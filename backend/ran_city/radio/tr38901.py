"""3GPP TR 38.901 path loss and LOS probability models.

Implements LOS probability (Clause 7.4.2, Table 7.4.2-1),
stochastic/deterministic LOS state sampling,
and UMa / UMi-Street Canyon path loss models (Clause 7.4.1, Table 7.4.1-1)
with decoupling calibration hooks (CalibrationParams).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ran_city.domain.grid import GridGeometry
from ran_city.domain.models import CellType

SPEED_OF_LIGHT_M_S: float = 299_792_458.0


@dataclass(frozen=True, slots=True)
class CalibrationParams:
    """Drive-test calibration coefficients decoupled from propagation formulas.

    Adds Delta L = offset_db + dist_log_delta * log10(d3d) + freq_log_delta * log10(fc)
    to the computed path loss matrix.
    """

    offset_db: float = 0.0
    dist_log_delta: float = 0.0
    freq_log_delta: float = 0.0


@dataclass(frozen=True, slots=True)
class PropagationMatrix:
    """Isotropic path loss matrix and line-of-sight status across a simulation grid."""

    loss_db: np.ndarray
    los_mask: np.ndarray
    pr_los: np.ndarray


DEFAULT_CALIBRATION = CalibrationParams()


def los_probability(
    d2d_m: float | np.ndarray,
    cell_type: CellType,
    h_ut_m: float = 1.5,
) -> float | np.ndarray:
    """Calculate the probability of Line-of-Sight (Pr_LOS).

    Follows 3GPP TR 38.901 v17.1.0, Table 7.4.2-1.

    Args:
        d2d_m: 2D horizontal distance in meters (scalar or array).
        cell_type: MACRO (UMa) or MICRO/PICO (UMi - Street Canyon).
        h_ut_m: User terminal height above ground in meters (default: 1.5 m).

    Returns:
        Probability of LOS in [0.0, 1.0] as float or np.ndarray.
    """
    is_scalar = np.isscalar(d2d_m)
    d2d = np.asarray(d2d_m, dtype=float)

    safe_d = np.where(d2d > 18.0, d2d, 18.0)

    if cell_type in (CellType.MICRO, CellType.PICO):
        # UMi - Street Canyon
        pr = (18.0 / safe_d) + np.exp(-safe_d / 36.0) * (1.0 - 18.0 / safe_d)
    elif cell_type == CellType.MACRO:
        # UMa
        c_prime = 0.0 if h_ut_m <= 13.0 else ((min(float(h_ut_m), 23.0) - 13.0) / 10.0) ** 1.5
        base = (18.0 / safe_d) + np.exp(-safe_d / 63.0) * (1.0 - 18.0 / safe_d)
        boost = 1.0 + c_prime * (5.0 / 4.0) * ((safe_d / 100.0) ** 3) * np.exp(-safe_d / 150.0)
        pr = np.minimum(1.0, base * boost)
    else:
        raise ValueError(f"Unsupported cell_type: {cell_type}")

    res = np.where(d2d <= 18.0, 1.0, pr)

    if is_scalar:
        return float(res)
    return res


def sample_los_mask(pr_los: np.ndarray, seed: int = 42) -> np.ndarray:
    """Generate a reproducible boolean LOS mask from LOS probability matrix."""
    rng = np.random.default_rng(seed)
    return rng.random(size=pr_los.shape) < pr_los


def compute_propagation_matrix(
    cell_type: CellType,
    freq_ghz: float,
    h_bs_m: float,
    h_ut_m: float,
    grid_geom: GridGeometry,
    seed: int = 42,
    los_mask: np.ndarray | None = None,
    calibration: CalibrationParams = DEFAULT_CALIBRATION,
) -> PropagationMatrix:
    """Compute the isotropic path loss matrix (L_prop) across a ScenarioGrid.

    Follows 3GPP TR 38.901 v17.1.0, Table 7.4.1-1 (UMa and UMi - Street Canyon).

    Args:
        cell_type: Deployment category (MACRO for UMa, MICRO/PICO for UMi).
        freq_ghz: Carrier frequency in GHz (0.5 <= freq_ghz <= 100.0).
        h_bs_m: Base station antenna height in meters.
        h_ut_m: User terminal antenna height in meters.
        grid_geom: Precalculated 2D geometry tensor from BS to grid.
        seed: Random seed for stochastic LOS Bernoulli trials (default: 42).
        los_mask: Optional explicit boolean LOS mask (overrides stochastic sampling).
        calibration: CalibrationParams offset and slope adjustments.

    Returns:
        PropagationMatrix containing loss_db, los_mask, and pr_los.
    """
    if not (0.5 <= freq_ghz <= 100.0):
        raise ValueError(f"freq_ghz must be in [0.5, 100.0] GHz, got {freq_ghz}")
    if h_bs_m <= 0.0:
        raise ValueError(f"h_bs_m must be strictly positive, got {h_bs_m}")
    if h_ut_m < 0.0:
        raise ValueError(f"h_ut_m must be non-negative, got {h_ut_m}")

    pr_los = np.asarray(
        los_probability(grid_geom.d2d_m, cell_type=cell_type, h_ut_m=h_ut_m),
        dtype=float,
    )

    if los_mask is None:
        mask = sample_los_mask(pr_los, seed=seed)
    else:
        if los_mask.shape != grid_geom.d2d_m.shape:
            raise ValueError(
                f"los_mask shape {los_mask.shape} does not match grid shape {grid_geom.d2d_m.shape}"
            )
        mask = np.asarray(los_mask, dtype=bool)

    # Breakpoint distance according to TR 38.901 Table 7.4.1-1 Note 1
    h_bs_eff = max(0.5, float(h_bs_m) - 1.0)
    h_ut_eff = max(0.5, float(h_ut_m) - 1.0)
    d_bp_m = 4.0 * h_bs_eff * h_ut_eff * (float(freq_ghz) * 1e9) / SPEED_OF_LIGHT_M_S

    d2d = grid_geom.d2d_m
    d3d = np.maximum(1.0, grid_geom.d3d_m)
    log_d3d = np.log10(d3d)
    log_fc = np.log10(float(freq_ghz))
    dh = float(h_bs_m) - float(h_ut_m)

    if cell_type == CellType.MACRO:
        # UMa (Table 7.4.1-1)
        pl1 = 28.0 + 22.0 * log_d3d + 20.0 * log_fc
        pl2 = 28.0 + 40.0 * log_d3d + 20.0 * log_fc - 9.0 * np.log10(d_bp_m**2 + dh**2)
        pl_los = np.where(d2d <= d_bp_m, pl1, pl2)
        pl_nlos_prime = 13.54 + 39.08 * log_d3d + 20.0 * log_fc - 0.6 * (float(h_ut_m) - 1.5)
        pl_nlos = np.maximum(pl_los, pl_nlos_prime)
    elif cell_type in (CellType.MICRO, CellType.PICO):
        # UMi - Street Canyon (Table 7.4.1-1)
        pl1 = 32.4 + 21.0 * log_d3d + 20.0 * log_fc
        pl2 = 32.4 + 40.0 * log_d3d + 20.0 * log_fc - 9.5 * np.log10(d_bp_m**2 + dh**2)
        pl_los = np.where(d2d <= d_bp_m, pl1, pl2)
        pl_nlos_prime = 22.4 + 35.3 * log_d3d + 21.3 * log_fc - 0.3 * (float(h_ut_m) - 1.5)
        pl_nlos = np.maximum(pl_los, pl_nlos_prime)
    else:
        raise ValueError(f"Unsupported cell_type: {cell_type}")

    base_loss = np.where(mask, pl_los, pl_nlos)
    cal_delta = (
        calibration.offset_db
        + calibration.dist_log_delta * log_d3d
        + calibration.freq_log_delta * log_fc
    )
    final_loss = base_loss + cal_delta

    return PropagationMatrix(
        loss_db=final_loss,
        los_mask=mask,
        pr_los=pr_los,
    )
