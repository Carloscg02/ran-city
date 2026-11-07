"""Decoupled 5G NR coverage calculations, power per RE, and multicell scenario aggregation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ran_city.antenna.tr38901 import compute_antenna_gain_matrix
from ran_city.domain.grid import GridGeometry, ScenarioGrid
from ran_city.domain.models import Cell, NrBand, Sector, Site
from ran_city.domain.units import Dbm
from ran_city.radio.tr38901 import (
    DEFAULT_CALIBRATION,
    CalibrationParams,
    PropagationMatrix,
    compute_propagation_matrix,
)

BOLTZMANN_K_J_K: float = 1.380649e-23


def thermal_noise_dbm(
    bandwidth_hz: float,
    noise_figure_db: float = 9.0,
    temperature_k: float = 290.0,
) -> Dbm:
    """Calculate thermal noise power in dBm: N = 10*log10(k_B * T * B * 1000) + F_dB.

    Follows 3GPP TS 38.101-1 Clause 7.3 and TS 38.104.

    Args:
        bandwidth_hz: Bandwidth in Hertz (e.g. subcarrier spacing or full channel).
        noise_figure_db: Receiver noise figure in dB (default: 9.0 dB for UE in FR1).
        temperature_k: Absolute noise temperature in Kelvin (default: 290.0 K).

    Returns:
        Thermal noise power as a Dbm instance.
    """
    if bandwidth_hz <= 0.0:
        raise ValueError(f"bandwidth_hz must be strictly positive, got {bandwidth_hz}")
    if temperature_k <= 0.0:
        raise ValueError(f"temperature_k must be strictly positive, got {temperature_k}")

    n0_mw_hz = BOLTZMANN_K_J_K * float(temperature_k) * 1000.0
    val = (
        10.0 * math.log10(n0_mw_hz)
        + 10.0 * math.log10(float(bandwidth_hz))
        + float(noise_figure_db)
    )
    return Dbm(val)


def re_thermal_noise_dbm(
    band: NrBand,
    noise_figure_db: float = 9.0,
    temperature_k: float = 290.0,
) -> Dbm:
    """Calculate thermal noise power per Resource Element (1 subcarrier, SCS kHz)."""
    subcarrier_bw_hz = float(band.scs_khz) * 1000.0
    return thermal_noise_dbm(
        bandwidth_hz=subcarrier_bw_hz,
        noise_figure_db=noise_figure_db,
        temperature_k=temperature_k,
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
        prop_matrix.loss_db + cell.cable_loss_db + rx_loss_db - antenna_gain_dbi - rx_gain_dbi
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
    noise_per_re_dbm: float
    interference_mw: np.ndarray
    sinr_db: np.ndarray


def compute_scenario_coverage(
    sites: Sequence[Site],
    grid: ScenarioGrid,
    seed: int = 42,
    calibration: CalibrationParams = DEFAULT_CALIBRATION,
    los_mask_override: bool | None = None,
    rx_gain_dbi: float = 0.0,
    rx_loss_db: float = 0.0,
    network_alias: str | None = None,
    n_band: int | None = None,
    ue_noise_figure_db: float = 9.0,
    temperature_k: float = 290.0,
    cell_load_factor: float = 1.0,
    include_shadow_fading: bool = False,
) -> ScenarioCoverageResult:
    """Compute multicell coverage, best server, serving RSRP, and co-channel SINR.

    Args:
        sites: Sequence of Sites with sectors and cells.
        grid: Geographical Simulation Grid (EPSG:25830).
        seed: Base seed for reproducible LOS trials.
        calibration: Drive-test calibration coefficients.
        los_mask_override: Optional boolean flag forcing all pixels to LOS (True) or NLOS (False).
        rx_gain_dbi: Receiver antenna gain (dBi).
        rx_loss_db: Receiver body/cable loss (dB).
        network_alias: Optional operator filter (e.g. 'Red A') isolating co-channel network.
        n_band: Optional NR band number filter (e.g. 78 for n78) isolating carrier layer.
        ue_noise_figure_db: Receiver UE noise figure in dB (default: 9.0 dB).
        temperature_k: Absolute noise temperature in Kelvin (default: 290.0 K).
        cell_load_factor: Traffic load factor eta in [0.0, 1.0] scaling interfering cells (default: 1.0).
        include_shadow_fading: Whether to include 2D correlated log-normal shadow fading (default: False).

    Returns:
        ScenarioCoverageResult with serving RSRP, best server index, interference (mW), and SINR (dB).
    """
    if not (0.0 <= cell_load_factor <= 1.0):
        raise ValueError(f"cell_load_factor must be in [0.0, 1.0], got {cell_load_factor}")

    active_cells: list[tuple[Site, Sector, Cell]] = []
    for site in sites:
        if network_alias is not None and site.network_alias != network_alias:
            continue
        for sector in site.sectors:
            for cell in sector.cells:
                if not cell.active:
                    continue
                if n_band is not None and cell.band.n_band != n_band:
                    continue
                active_cells.append((site, sector, cell))

    if not active_cells:
        raise ValueError("No active cells found matching the filtering criteria")

    # Guardrail: prohibit illegal mixing of different operators or orthogonal bands
    distinct_networks = {site.network_alias for site, _, _ in active_cells}
    distinct_bands = {cell.band.n_band for _, _, cell in active_cells}
    if len(distinct_networks) > 1 or len(distinct_bands) > 1:
        raise ValueError(
            f"Cannot compute co-channel coverage with mixed networks {distinct_networks} "
            f"or mixed bands {distinct_bands}. Specify network_alias and n_band to isolate a single co-channel layer."
        )

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
            include_shadow_fading=include_shadow_fading,
            resolution_m=grid.environment.resolution_m,
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

    # Reference RE thermal noise calculation
    reference_band = active_cells[0][2].band
    noise_per_re_dbm = re_thermal_noise_dbm(
        band=reference_band,
        noise_figure_db=ue_noise_figure_db,
        temperature_k=temperature_k,
    ).value
    noise_per_re_mw = 10.0 ** (noise_per_re_dbm / 10.0)

    power_mw_stack = 10.0 ** (rsrp_stack / 10.0)
    serving_mw = 10.0 ** (serving_rsrp_dbm / 10.0)

    if len(active_cells) == 1 or cell_load_factor == 0.0:
        interference_mw = np.zeros(grid.shape, dtype=float)
    else:
        cell_indices = np.arange(len(active_cells))[:, None, None]
        interferer_mask = cell_indices != best_server_idx[None, :, :]
        non_serving_mw = np.sum(np.where(interferer_mask, power_mw_stack, 0.0), axis=0)
        interference_mw = float(cell_load_factor) * non_serving_mw

    sinr_linear = serving_mw / (interference_mw + noise_per_re_mw)
    sinr_db = 10.0 * np.log10(sinr_linear)

    return ScenarioCoverageResult(
        cell_ids=tuple(cell_ids),
        per_cell=tuple(per_cell),
        serving_rsrp_dbm=serving_rsrp_dbm,
        best_server_idx=best_server_idx,
        noise_per_re_dbm=noise_per_re_dbm,
        interference_mw=interference_mw,
        sinr_db=sinr_db,
    )
