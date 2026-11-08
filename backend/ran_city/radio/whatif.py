"""Immutable What-If scenario modification engine for 5G NR sites, sectors, and cells."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ran_city.domain.models import Site


@dataclass(frozen=True, slots=True)
class CellOverride:
    """Ephemeral modification parameters for an individual cell."""

    cell_id: str
    mechanical_tilt_deg: float | None = None
    electrical_tilt_deg: float | None = None
    electrical_scan_deg: float | None = None
    tx_power_dbm: float | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class SectorOverride:
    """Ephemeral modification parameters for a radiating sector."""

    sector_id: str
    azimuth_deg: float | None = None
    ant_height_m: float | None = None


def apply_whatif_overrides(
    sites: Sequence[Site],
    cell_overrides: Sequence[CellOverride] = (),
    sector_overrides: Sequence[SectorOverride] = (),
) -> tuple[Site, ...]:
    """Apply What-If modifications immutably, returning a new collection of Sites.

    The original Site instances remain completely untouched.

    Args:
        sites: Sequence of base Site instances.
        cell_overrides: Sequence of cell-level modifications.
        sector_overrides: Sequence of sector-level modifications.

    Returns:
        New tuple of Site instances with updated parameters.

    Raises:
        ValueError: If any cell_id or sector_id specified in overrides does not exist in sites.
    """
    if not cell_overrides and not sector_overrides:
        return tuple(sites)

    # Validate that all requested cell_ids and sector_ids exist
    known_cells: set[str] = set()
    known_sectors: set[str] = set()
    for site in sites:
        for sector in site.sectors:
            known_sectors.add(sector.sector_id)
            for cell in sector.cells:
                known_cells.add(cell.cell_id)

    for cell_ovr in cell_overrides:
        if cell_ovr.cell_id not in known_cells:
            raise ValueError(f"Cell ID '{cell_ovr.cell_id}' not found in scenario")

    for sector_ovr in sector_overrides:
        if sector_ovr.sector_id not in known_sectors:
            raise ValueError(f"Sector ID '{sector_ovr.sector_id}' not found in scenario")

    cell_ovr_map = {ovr.cell_id: ovr for ovr in cell_overrides}
    sector_ovr_map = {ovr.sector_id: ovr for ovr in sector_overrides}

    updated_sites: list[Site] = []
    for site in sites:
        updated_sectors = []
        site_changed = False

        for sector in site.sectors:
            updated_cells = []
            sector_cells_changed = False

            for cell in sector.cells:
                if cell.cell_id in cell_ovr_map:
                    covr = cell_ovr_map[cell.cell_id]
                    antenna_updates = {}
                    if covr.mechanical_tilt_deg is not None:
                        antenna_updates["mechanical_tilt_deg"] = covr.mechanical_tilt_deg
                    if covr.electrical_tilt_deg is not None:
                        antenna_updates["electrical_tilt_deg"] = covr.electrical_tilt_deg
                    if covr.electrical_scan_deg is not None:
                        antenna_updates["electrical_scan_deg"] = covr.electrical_scan_deg

                    cell_updates = {}
                    if antenna_updates:
                        cell_updates["antenna"] = cell.antenna.model_copy(update=antenna_updates)
                    if covr.tx_power_dbm is not None:
                        cell_updates["tx_power_dbm"] = covr.tx_power_dbm
                    if covr.active is not None:
                        cell_updates["active"] = covr.active

                    if cell_updates:
                        updated_cell = cell.model_copy(update=cell_updates)
                        sector_cells_changed = True
                    else:
                        updated_cell = cell
                else:
                    updated_cell = cell
                updated_cells.append(updated_cell)

            sector_updates = {}
            if sector_cells_changed:
                sector_updates["cells"] = tuple(updated_cells)

            if sector.sector_id in sector_ovr_map:
                sovr = sector_ovr_map[sector.sector_id]
                if sovr.azimuth_deg is not None:
                    sector_updates["azimuth_deg"] = sovr.azimuth_deg
                if sovr.ant_height_m is not None:
                    sector_updates["ant_height_m"] = sovr.ant_height_m

            if sector_updates:
                updated_sector = sector.model_copy(update=sector_updates)
                site_changed = True
            else:
                updated_sector = sector
            updated_sectors.append(updated_sector)

        if site_changed:
            updated_site = site.model_copy(update={"sectors": tuple(updated_sectors)})
        else:
            updated_site = site
        updated_sites.append(updated_site)

    return tuple(updated_sites)
