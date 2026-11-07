"""Ingestion CLI pipeline for Jaén: OpenCelliD (MCC=214) + OpenStreetMap masts + city schema."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence
from pathlib import Path

import httpx
import numpy as np

from ran_city.data_sources.city_schema import (
    CityConfig,
    CityScenario,
    CityZoneSpec,
    OperatorSpectrumSpec,
    save_city_scenario,
)
from ran_city.data_sources.opencellid_osm import (
    OsmMastRecord,
    RawCellRecord,
    cluster_opencellid_and_snap_osm,
)
from ran_city.domain.grid import EnvironmentType
from ran_city.geo.crs import wgs84_to_utm30

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_jaen")

# Jaén city simulation bounding box: lon in [-3.825, -3.765], lat in [37.760, 37.800]
JAEN_BBOX_WGS84 = (-3.825, 37.760, -3.765, 37.800)  # min_lon, min_lat, max_lon, max_lat

# Curated reference OSM telecom masts and towers across Jaén (used directly or as fallback)
JAEN_CURATED_OSM_MASTS: list[OsmMastRecord] = [
    OsmMastRecord(osm_id="OSM_SANTA_CATALINA", lon=-3.7972, lat=37.7681, mast_type="tower"),
    OsmMastRecord(osm_id="OSM_SAN_CRISTOBAL", lon=-3.8050, lat=37.7730, mast_type="mast"),
    OsmMastRecord(osm_id="OSM_ESTACION_RENFE", lon=-3.7885, lat=37.7788, mast_type="mast"),
    OsmMastRecord(osm_id="OSM_LOS_OLIVARES", lon=-3.7810, lat=37.7950, mast_type="tower"),
    OsmMastRecord(osm_id="OSM_UNIVERSIDAD", lon=-3.7780, lat=37.7875, mast_type="mast"),
    OsmMastRecord(osm_id="OSM_GRAN_EJE", lon=-3.8005, lat=37.7795, mast_type="mast"),
    OsmMastRecord(osm_id="OSM_CATEDRAL", lon=-3.7895, lat=37.7655, mast_type="tower"),
    OsmMastRecord(osm_id="OSM_BULEVAR", lon=-3.7845, lat=37.7845, mast_type="mast"),
    OsmMastRecord(osm_id="OSM_POLIGONO_ESTE", lon=-3.7710, lat=37.7920, mast_type="tower"),
    OsmMastRecord(osm_id="OSM_VALDEASTILLAS", lon=-3.8180, lat=37.7750, mast_type="mast"),
    OsmMastRecord(osm_id="OSM_PEJUELA", lon=-3.7820, lat=37.7710, mast_type="mast"),
    OsmMastRecord(osm_id="OSM_EJIDO", lon=-3.7950, lat=37.7620, mast_type="mast"),
]


# Curated seed cell records (OpenCelliD MCC=214 in Jaén BBox) for deterministic offline fallback
JAEN_CURATED_SEED_CELLS: list[RawCellRecord] = [
    # Red A (MNC 7) - North (Los Olivares / Polígono), Center (Bulevar / Lagunillas / Renfe), South (Catedral / Santa Catalina)
    RawCellRecord(mcc=214, mnc=7, cell_id=70101, radio="NR", lon=-3.7810, lat=37.7950),
    RawCellRecord(mcc=214, mnc=7, cell_id=70102, radio="LTE", lon=-3.7764, lat=37.7916),
    RawCellRecord(mcc=214, mnc=7, cell_id=70103, radio="NR", lon=-3.8190, lat=37.7851),
    RawCellRecord(mcc=214, mnc=7, cell_id=70104, radio="NR", lon=-3.7885, lat=37.7788),
    RawCellRecord(mcc=214, mnc=7, cell_id=70105, radio="LTE", lon=-3.7878, lat=37.7732),
    RawCellRecord(mcc=214, mnc=7, cell_id=70106, radio="NR", lon=-3.7972, lat=37.7681),
    # Red B (MNC 1) - North (Polígono Este / Olivares), Center (Bulevar / Gran Eje), South (Peñuelas / Catedral)
    RawCellRecord(mcc=214, mnc=1, cell_id=10201, radio="NR", lon=-3.7710, lat=37.7920),
    RawCellRecord(mcc=214, mnc=1, cell_id=10202, radio="LTE", lon=-3.8080, lat=37.7871),
    RawCellRecord(mcc=214, mnc=1, cell_id=10203, radio="NR", lon=-3.7780, lat=37.7875),
    RawCellRecord(mcc=214, mnc=1, cell_id=10204, radio="NR", lon=-3.7802, lat=37.7730),
    RawCellRecord(mcc=214, mnc=1, cell_id=10205, radio="LTE", lon=-3.8050, lat=37.7730),
    RawCellRecord(mcc=214, mnc=1, cell_id=10206, radio="NR", lon=-3.7895, lat=37.7655),
    # Red C (MNC 3) - North (Olivares), Center (Universidad / Bulevar / Valdeastillas), South (Peñuelas / Ejido)
    RawCellRecord(mcc=214, mnc=3, cell_id=30301, radio="NR", lon=-3.7769, lat=37.7901),
    RawCellRecord(mcc=214, mnc=3, cell_id=30302, radio="LTE", lon=-3.8080, lat=37.7861),
    RawCellRecord(mcc=214, mnc=3, cell_id=30303, radio="NR", lon=-3.7707, lat=37.7791),
    RawCellRecord(mcc=214, mnc=3, cell_id=30304, radio="NR", lon=-3.8005, lat=37.7795),
    RawCellRecord(mcc=214, mnc=3, cell_id=30305, radio="LTE", lon=-3.7820, lat=37.7720),
    RawCellRecord(mcc=214, mnc=3, cell_id=30306, radio="NR", lon=-3.7950, lat=37.7620),
]


def fetch_opencellid_jaen(
    api_key: str,
    bbox: tuple[float, float, float, float] = JAEN_BBOX_WGS84,
    tile_step_deg: float = 0.012,
) -> list[RawCellRecord]:
    """Query OpenCelliD API for cells within the Jaén bounding box by subdividing into small tiles."""
    min_lon, min_lat, max_lon, max_lat = bbox
    raw_cells: list[RawCellRecord] = []
    seen_keys: set[tuple[int, int, str | int]] = set()

    lat_tiles = np.arange(min_lat, max_lat, tile_step_deg)
    lon_tiles = np.arange(min_lon, max_lon, tile_step_deg)

    with httpx.Client(timeout=8.0) as client:
        for t_lat in lat_tiles:
            for t_lon in lon_tiles:
                t_lat_max = min(max_lat, float(t_lat + tile_step_deg))
                t_lon_max = min(max_lon, float(t_lon + tile_step_deg))
                bbox_str = f"{t_lat:.4f},{t_lon:.4f},{t_lat_max:.4f},{t_lon_max:.4f}"
                try:
                    resp = client.get(
                        "https://opencellid.org/cell/getInArea",
                        params={
                            "key": api_key,
                            "BBOX": bbox_str,
                            "mcc": 214,
                            "format": "json",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for c in data.get("cells", []):
                            lon = float(c.get("lon"))
                            lat = float(c.get("lat"))
                            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                                continue
                            mcc = int(c.get("mcc", 214))
                            mnc = int(c.get("mnc", 0))
                            cid = c.get("cellid")
                            dedup_key = (mcc, mnc, cid)
                            if dedup_key in seen_keys:
                                continue
                            seen_keys.add(dedup_key)

                            raw_cells.append(
                                RawCellRecord(
                                    mcc=mcc,
                                    mnc=mnc,
                                    cell_id=cid,
                                    radio=c.get("radio", "LTE"),
                                    lon=lon,
                                    lat=lat,
                                    lac=c.get("lac"),
                                    range_m=float(c.get("range", 1000.0)),
                                    samples=int(c.get("samples", 1)),
                                )
                            )
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    logger.debug("Tile query %s failed: %s", bbox_str, exc)

    logger.info("Fetched %d unique OpenCelliD cells in Jaén", len(raw_cells))
    return raw_cells


def fetch_osm_masts_jaen(
    bbox: tuple[float, float, float, float] = JAEN_BBOX_WGS84,
) -> list[OsmMastRecord]:
    """Query Overpass API for masts and towers in Jaén, falling back to curated reference masts."""
    min_lon, min_lat, max_lon, max_lat = bbox
    overpass_endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    query = f"""
    [out:json][timeout:10];
    (
      node["man_made"="mast"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["man_made"="tower"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["man_made"="communications_tower"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out body;
    """
    for ep in overpass_endpoints:
        try:
            resp = httpx.post(
                ep,
                data={"data": query},
                headers={"User-Agent": "RAN-city-Research/1.0"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                if elements:
                    masts = [
                        OsmMastRecord(
                            osm_id=el.get("id"),
                            lon=float(el.get("lon")),
                            lat=float(el.get("lat")),
                            mast_type=el.get("tags", {}).get("man_made", "mast"),
                        )
                        for el in elements
                    ]
                    logger.info("Retrieved %d masts from Overpass (%s)", len(masts), ep)
                    return masts
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.debug("Overpass endpoint %s failed: %s", ep, exc)
            continue

    logger.info("Using curated OSM masts for Jaén (%d masts)", len(JAEN_CURATED_OSM_MASTS))
    return JAEN_CURATED_OSM_MASTS


def build_jaen_scenario(
    cells: Sequence[RawCellRecord],
    masts: Sequence[OsmMastRecord],
    cluster_radius_m: float = 250.0,
    osm_snap_radius_m: float = 85.0,
    sites_per_operator: int = 6,
) -> CityScenario:
    """Cluster cells, snap to masts, and assemble a complete, validated CityScenario."""
    min_lon, min_lat, max_lon, max_lat = JAEN_BBOX_WGS84
    min_x, min_y = wgs84_to_utm30(min_lon, min_lat)
    max_x, max_y = wgs84_to_utm30(max_lon, max_lat)

    config = CityConfig(
        city_id="jaen",
        city_name="Jaén",
        bbox_wgs84=(min_lon, min_lat, max_lon, max_lat),
        bbox_utm30=(float(min_x), float(min_y), float(max_x), float(max_y)),
        zones=[
            CityZoneSpec(
                zone_id="dense_urban",
                name="Casco Histórico y Centro Comercial",
                environment=EnvironmentType.DENSE_URBAN,
                description="Alta densidad urbana y cañones de calles (Catedral, Carrera, San Ildefonso)",
            ),
            CityZoneSpec(
                zone_id="urban",
                name="Bulevar y Campus Las Lagunillas",
                environment=EnvironmentType.URBAN,
                description="Ensanche moderno, bulevar residencial y campus universitario",
            ),
            CityZoneSpec(
                zone_id="rural",
                name="Cerro de Santa Catalina y Vega Periurbana",
                environment=EnvironmentType.RURAL,
                description="Relieve pronunciado y entorno rural periurbano",
            ),
        ],
        operators=[
            OperatorSpectrumSpec(
                network_alias="Red A",
                mcc=214,
                mnc=7,
                cnaf_blocks=["n28", "n78"],
            ),
            OperatorSpectrumSpec(
                network_alias="Red B",
                mcc=214,
                mnc=1,
                cnaf_blocks=["n28", "n78"],
            ),
            OperatorSpectrumSpec(
                network_alias="Red C",
                mcc=214,
                mnc=3,
                cnaf_blocks=["n28", "n78"],
            ),
        ],
    )

    all_sites = cluster_opencellid_and_snap_osm(
        cells=cells,
        masts=masts,
        cluster_radius_m=cluster_radius_m,
        osm_snap_radius_m=osm_snap_radius_m,
    )

    # Filter to select a representative, spatially distributed set per operator inside bbox_utm30
    selected_sites = []
    for alias in ["Red A", "Red B", "Red C"]:
        op_sites = [
            s
            for s in all_sites
            if s.network_alias == alias
            and (min_x <= s.x_m <= max_x)
            and (min_y <= s.y_m <= max_y)
        ]
        if not op_sites:
            continue
        # Sort by y_m descending to distribute from north (Bulevar/Polígono) to south (Santa Catalina/Catedral)
        op_sites.sort(key=lambda s: s.y_m, reverse=True)
        # Select evenly spaced sites spanning both northern low-elevation and southern high-elevation ends
        if len(op_sites) <= sites_per_operator:
            sampled = op_sites
        else:
            indices = np.linspace(0, len(op_sites) - 1, sites_per_operator, dtype=int)
            seen_idx: set[int] = set()
            sampled = []
            for i in indices:
                idx_int = int(i)
                if idx_int not in seen_idx:
                    seen_idx.add(idx_int)
                    sampled.append(op_sites[idx_int])
        # Re-index site IDs cleanly
        for idx, site in enumerate(sampled, start=1):
            clean_id = f"SITE_{alias.replace(' ', '_').upper()}_{idx:02d}"
            # Recreate site with clean sequential ID and matching sector IDs
            new_sectors = []
            for sec in site.sectors:
                new_sec_id = f"{clean_id}_S{int(sec.azimuth_deg)}"
                new_cells = []
                for c in sec.cells:
                    band_suffix = f"n{c.band.n_band}"
                    new_cell = c.model_copy(update={"cell_id": f"{new_sec_id}_{band_suffix}"})
                    new_cells.append(new_cell)
                new_sec = sec.model_copy(
                    update={"sector_id": new_sec_id, "cells": tuple(new_cells)}
                )
                new_sectors.append(new_sec)

            clean_site = site.model_copy(
                update={"site_id": clean_id, "sectors": tuple(new_sectors)}
            )
            selected_sites.append(clean_site)

    logger.info("Selected %d representative sites across operators", len(selected_sites))
    return CityScenario(config=config, sites=selected_sites)


def main() -> None:
    """CLI entry point for Jaén data ingestion."""
    parser = argparse.ArgumentParser(description="Ingest Jaén cells and OSM masts into jaen.yaml")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/cities/jaen.yaml"),
        help="Target output YAML file path",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENCELLID_API_KEY", "").strip()
    if api_key:
        logger.info("Querying OpenCelliD for Jaén (BBox: %s)...", JAEN_BBOX_WGS84)
        raw_cells = fetch_opencellid_jaen(api_key, JAEN_BBOX_WGS84)
        if not raw_cells:
            logger.warning("No cells retrieved from OpenCelliD. Falling back to curated seed data.")
            raw_cells = JAEN_CURATED_SEED_CELLS
    else:
        logger.warning(
            "OPENCELLID_API_KEY environment variable not found. Using curated seed data."
        )
        raw_cells = JAEN_CURATED_SEED_CELLS

    logger.info("Querying OpenStreetMap masts for Jaén...")
    osm_masts = fetch_osm_masts_jaen(JAEN_BBOX_WGS84)

    logger.info("Clustering and assembling scenario...")
    scenario = build_jaen_scenario(raw_cells, osm_masts)

    save_city_scenario(scenario, args.output)
    logger.info("Successfully persisted Jaén scenario to %s", args.output)


if __name__ == "__main__":
    main()
