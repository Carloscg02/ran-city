"""Decoupled 5G NR coverage calculations, power per RE, and multicell scenario aggregation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ran_city.antenna.tr38901 import compute_antenna_gain_matrix
from ran_city.domain.grid import GridGeometry, ScenarioGrid
from ran_city.domain.models import Cell, Sector, Site
from ran_city.domain.units import Dbm
from ran_city.radio.tr38901 import (
    DEFAULT_CALIBRATION,
    CalibrationParams,
    PropagationMatrix,
    compute_propagation_matrix,
)


def power_per_re_dbm(tx_power_dbm: float, num_rbs: int) -> Dbm:
    """Calculate the transmit power allocated per Resource Element (RE).

    Follows 3GPP TS 38.215 Clause 5.1.1 and TS 38.211 Clause 4.4.4.1 (12 subcarriers per RB).
    P_TX,RE (dBm) = P_TX,total (dBm) - 10 * log10(12 * N_RB)

    Args:
        tx_power_dbm: Total cell transmit power in dBm.
        num_rbs: Number of active Resource Blocks (N_RB >= 1).

    Returns:
        Power per Resource Element as a Dbm instance.
    """
    if num_rbs < 1:
        raise ValueError(f"num_rbs must be >= 1, got {num_rbs}")
    val = float(tx_power_dbm) - 10.0 * math.log10(12.0 * float(num_rbs))
    return Dbm(val)


@dataclass(frozen=True, slots=True)
class CellCoverageResult:
    """Coverage matrices for an individual cell."""

    cell_id: str
    tx_power_per_re_dbm: float
    antenna_gain_dbi: np.ndarray
    effective_loss_db: np.ndarray
    rsrp_dbm: np.ndarray


def compute_cell_coverage(
    cell: Cell,
    sector_azimuth_deg: float,
    grid_geom: GridGeometry,
    prop_matrix: PropagationMatrix,
    rx_gain_dbi: float = 0.0,
    rx_loss_db: float = 0.0,
) -> CellCoverageResult:
    """Compute effective loss and RSRP matrices for a single cell.

    L_eff = L_prop + L_TX_cable + L_RX - G_ant - G_RX
    RSRP = P_TX,RE - L_eff

    This computation is completely decoupled from the propagation matrix,
    allowing tilts and powers to change without recalculating path loss.
    """
    antenna_gain_dbi = compute_antenna_gain_matrix(cell.antenna, sector_azimuth_deg, grid_geom)
    effective_loss_db = (
        prop_matrix.loss_db
        + cell.cable_loss_db
        + rx_loss_db
        - antenna_gain_dbi
        - rx_gain_dbi
    )
    p_re = power_per_re_dbm(cell.tx_power_dbm, cell.band.num_rbs).value
    rsrp_dbm = p_re - effective_loss_db

    return CellCoverageResult(
        cell_id=cell.cell_id,
        tx_power_per_re_dbm=p_re,
        antenna_gain_dbi=antenna_gain_dbi,
        effective_loss_db=effective_loss_db,
        rsrp_dbm=rsrp_dbm,
    )


@dataclass(frozen=True, slots=True)
class ScenarioCoverageResult:
    """Aggregated multicell coverage result for an entire geographic scenario."""

    cell_ids: tuple[str, ...]
    per_cell: tuple[CellCoverageResult, ...]
    serving_rsrp_dbm: np.ndarray
    best_server_idx: np.ndarray


def compute_scenario_coverage(
    sites: Sequence[Site],
    grid: ScenarioGrid,
    seed: int = 42,
    calibration: CalibrationParams = DEFAULT_CALIBRATION,
    los_mask_override: bool | None = None,
    rx_gain_dbi: float = 0.0,
    rx_loss_db: float = 0.0,
) -> ScenarioCoverageResult:
    """Compute multicell coverage, best server, and serving RSRP over a ScenarioGrid.

    Args:
        sites: Sequence of Sites with sectors and cells.
        grid: Geographical Simulation Grid (EPSG:25830).
        seed: Base seed for reproducible LOS trials.
        calibration: Drive-test calibration coefficients.
        los_mask_override: Optional boolean flag forcing all pixels to LOS (True) or NLOS (False).
        rx_gain_dbi: Receiver antenna gain (dBi).
        rx_loss_db: Receiver body/cable loss (dB).

    Returns:
        ScenarioCoverageResult with per-cell results, best_server_idx, and serving_rsrp_dbm.
    """
    active_cells: list[tuple[Site, Sector, Cell]] = []
    for site in sites:
        for sector in site.sectors:
            for cell in sector.cells:
                if cell.active:
                    active_cells.append((site, sector, cell))

    if not active_cells:
        raise ValueError("No active cells found in the provided sites")

    cell_ids: list[str] = []
    per_cell: list[CellCoverageResult] = []
    rsrp_list: list[np.ndarray] = []

    for idx, (site, sector, cell) in enumerate(active_cells):
        tx_pos = site.tx_position(sector)
        geom = grid.geometry_from_tx(tx_pos)

        explicit_mask = (
            None
            if los_mask_override is None
            else np.full(grid.shape, los_mask_override, dtype=bool)
        )

        prop = compute_propagation_matrix(
            cell_type=cell.cell_type,
            freq_ghz=cell.band.freq_ghz,
            h_bs_m=sector.ant_height_m,
            h_ut_m=grid.rx_height_m,
            grid_geom=geom,
            seed=seed + idx,
            los_mask=explicit_mask,
            calibration=calibration,
        )

        cov = compute_cell_coverage(
            cell=cell,
            sector_azimuth_deg=sector.azimuth_deg,
            grid_geom=geom,
            prop_matrix=prop,
            rx_gain_dbi=rx_gain_dbi,
            rx_loss_db=rx_loss_db,
        )

        cell_ids.append(cell.cell_id)
        per_cell.append(cov)
        rsrp_list.append(cov.rsrp_dbm)

    rsrp_stack = np.stack(rsrp_list, axis=0)
    serving_rsrp_dbm = np.max(rsrp_stack, axis=0)
    best_server_idx = np.argmax(rsrp_stack, axis=0)

    return ScenarioCoverageResult(
        cell_ids=tuple(cell_ids),
        per_cell=tuple(per_cell),
        serving_rsrp_dbm=serving_rsrp_dbm,
        best_server_idx=best_server_idx,
    )
