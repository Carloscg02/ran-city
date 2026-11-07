"""OpenCelliD and OpenStreetMap data ingestion, MNC mapping, clustering, and snapping."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ran_city.domain.models import (
    AntennaConfig,
    Cell,
    CellType,
    DataSourceOrigin,
    NrBand,
    Sector,
    Site,
)
from ran_city.geo.crs import wgs84_to_utm30

_MNC_MAP: dict[int, str] = {
    7: "Red A",  # Telefónica / Movistar
    1: "Red B",  # Vodafone
    3: "Red C",  # Orange / MásMóvil
}


def map_mnc_to_network_alias(mnc: int) -> str | None:
    """Map Spanish Mobile Network Code (MNC) to neutral educational network alias.

    Args:
        mnc: Mobile Network Code integer (e.g. 7, 1, 3).

    Returns:
        'Red A', 'Red B', 'Red C' or None if unmapped.
    """
    return _MNC_MAP.get(int(mnc))


@dataclass(frozen=True, slots=True)
class RawCellRecord:
    """Raw cell measurement or centroid record from OpenCelliD."""

    mcc: int
    mnc: int
    cell_id: str | int
    radio: str
    lon: float
    lat: float
    lac: int | None = None
    range_m: float = 1000.0
    samples: int = 1
    azimuth_deg: float | None = None


@dataclass(frozen=True, slots=True)
class OsmMastRecord:
    """Telecommunications mast or tower record from OpenStreetMap."""

    osm_id: str | int
    lon: float
    lat: float
    mast_type: str = "mast"


def estimate_jaen_ground_z(x_m: float, y_m: float) -> float:
    """Analytical hypsometric model of Jaén when DEM is not directly queried.

    Jaén topography slopes from Cerro de Santa Catalina (~815m) in the southwest / south
    down towards the Guadalbullón valley and Bulevar (~420m) in the north / northeast.
    """
    # Santa Catalina mountain peak ~ (429600, 4180200), peak elevation ~815m
    sc_dist = math.hypot(x_m - 429600.0, y_m - 4180200.0)
    sc_factor = max(0.0, 1.0 - sc_dist / 1600.0)
    sc_boost = 320.0 * (sc_factor**1.5)

    # Regional slope: north (higher y) is lower (valley ~415-445m), south (lower y) is higher (~570m + hill)
    dy_km = (y_m - 4181000.0) / 1000.0
    base_z = 525.0 - 42.0 * dy_km
    z = base_z + sc_boost
    return float(max(400.0, min(840.0, z)))


def cluster_opencellid_and_snap_osm(
    cells: Sequence[RawCellRecord],
    masts: Sequence[OsmMastRecord],
    cluster_radius_m: float = 120.0,
    osm_snap_radius_m: float = 75.0,
    default_ant_height_m: float = 25.0,
    default_tx_power_dbm: float = 43.0,
    ground_z_m: float | None = None,
) -> list[Site]:
    """Cluster raw cell records by operator and snap site locations to nearby OSM masts.

    Args:
        cells: Raw cell records (OpenCelliD).
        masts: OpenStreetMap masts and towers.
        cluster_radius_m: Spatial radius to group cells into the same physical base station.
        osm_snap_radius_m: Maximum distance to snap cluster centroid to an OSM mast.
        default_ant_height_m: Default sector antenna height in meters.
        default_tx_power_dbm: Default cell transmit power in dBm.
        ground_z_m: Optional explicit ground elevation override; if None, uses Jaén hypsometry.

    Returns:
        List of Site instances with ESTIMATED origin and configured sectors/cells (n28 + n78).
    """
    # Filter cells by mapped network alias
    mapped_cells: list[tuple[str, RawCellRecord, float, float]] = []
    for c in cells:
        alias = map_mnc_to_network_alias(c.mnc)
        if alias is not None:
            x_m, y_m = wgs84_to_utm30(c.lon, c.lat)
            mapped_cells.append((alias, c, float(x_m), float(y_m)))

    # Convert masts to UTM30
    projected_masts: list[tuple[OsmMastRecord, float, float]] = []
    for m in masts:
        mx, my = wgs84_to_utm30(m.lon, m.lat)
        projected_masts.append((m, float(mx), float(my)))

    # Group by network alias
    operators = sorted({item[0] for item in mapped_cells})
    resulting_sites: list[Site] = []

    for alias in operators:
        op_cells = [item for item in mapped_cells if item[0] == alias]
        # Sort cells for deterministic clustering
        op_cells.sort(key=lambda item: str(item[1].cell_id))

        clusters: list[list[tuple[RawCellRecord, float, float]]] = []
        cluster_centroids: list[list[float]] = []  # [x, y]

        for _, cell_rec, cx, cy in op_cells:
            assigned = False
            best_idx = -1
            best_dist = float("inf")

            for idx, (cent_x, cent_y) in enumerate(cluster_centroids):
                dist = math.hypot(cx - cent_x, cy - cent_y)
                if dist <= cluster_radius_m and dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            if best_idx >= 0:
                clusters[best_idx].append((cell_rec, cx, cy))
                # Update centroid
                xs = [p[1] for p in clusters[best_idx]]
                ys = [p[2] for p in clusters[best_idx]]
                cluster_centroids[best_idx] = [sum(xs) / len(xs), sum(ys) / len(ys)]
                assigned = True

            if not assigned:
                clusters.append([(cell_rec, cx, cy)])
                cluster_centroids.append([cx, cy])

        # For each cluster, snap to OSM mast if nearby
        for cluster_idx, (clust, (cent_x, cent_y)) in enumerate(
            zip(clusters, cluster_centroids, strict=True)
        ):
            site_x = cent_x
            site_y = cent_y

            # Find nearest mast
            min_mast_dist = float("inf")
            nearest_mast_pos: tuple[float, float] | None = None
            for _, mx, my in projected_masts:
                dist = math.hypot(mx - cent_x, my - cent_y)
                if dist < min_mast_dist:
                    min_mast_dist = dist
                    nearest_mast_pos = (mx, my)

            if nearest_mast_pos is not None and min_mast_dist <= osm_snap_radius_m:
                site_x, site_y = nearest_mast_pos

            site_id = f"SITE_{alias.replace(' ', '_').upper()}_{cluster_idx + 1:02d}"

            # Calculate realistic ground elevation
            if ground_z_m is not None:
                site_ground_z = float(ground_z_m)
            else:
                site_ground_z = round(estimate_jaen_ground_z(site_x, site_y), 1)

            # Build trisector configuration (0°, 120°, 240°)
            azimuths = (0.0, 120.0, 240.0)
            sectors: list[Sector] = []

            for az in azimuths:
                sec_id = f"{site_id}_S{int(az)}"
                cell_n28 = Cell(
                    cell_id=f"{sec_id}_n28",
                    cell_type=CellType.MACRO,
                    band=NrBand.n28(),
                    antenna=AntennaConfig(
                        n_rows=8,
                        n_cols=8,
                        mechanical_tilt_deg=0.0,
                        electrical_tilt_deg=6.0,
                    ),
                    tx_power_dbm=default_tx_power_dbm,
                    source=DataSourceOrigin.ESTIMATED,
                )
                cell_n78 = Cell(
                    cell_id=f"{sec_id}_n78",
                    cell_type=CellType.MACRO,
                    band=NrBand.n78(),
                    antenna=AntennaConfig(
                        n_rows=8,
                        n_cols=8,
                        mechanical_tilt_deg=0.0,
                        electrical_tilt_deg=6.0,
                    ),
                    tx_power_dbm=default_tx_power_dbm,
                    source=DataSourceOrigin.ESTIMATED,
                )
                sectors.append(
                    Sector(
                        sector_id=sec_id,
                        azimuth_deg=az,
                        ant_height_m=default_ant_height_m,
                        cells=(cell_n28, cell_n78),
                    )
                )

            site = Site(
                site_id=site_id,
                network_alias=alias,
                x_m=float(site_x),
                y_m=float(site_y),
                ground_z_m=site_ground_z,
                sectors=tuple(sectors),
                source=DataSourceOrigin.ESTIMATED,
            )
            resulting_sites.append(site)

    return resulting_sites
