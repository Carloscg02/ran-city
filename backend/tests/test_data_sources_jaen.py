"""Tests for data sources adapter: OpenCelliD clustering, OSM snapping, and Jaén scenario."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ran_city.domain.grid import EnvironmentType, ScenarioGrid
from ran_city.domain.models import DataSourceOrigin
from ran_city.radio.coverage import compute_scenario_coverage


class TestOpenCellIdOsmClustering:
    """Tests for raw OpenCelliD cell records clustering, MNC mapping, and OSM mast snapping."""

    def test_map_mnc_to_network_alias(self):
        from ran_city.data_sources.opencellid_osm import map_mnc_to_network_alias

        assert map_mnc_to_network_alias(7) == "Red A"  # Movistar / Telefónica
        assert map_mnc_to_network_alias(1) == "Red B"  # Vodafone
        assert map_mnc_to_network_alias(3) == "Red C"  # Orange / MásMóvil
        assert map_mnc_to_network_alias(99) is None

    def test_clustering_and_snap_osm(self):
        from ran_city.data_sources.opencellid_osm import (
            OsmMastRecord,
            RawCellRecord,
            cluster_opencellid_and_snap_osm,
        )
        from ran_city.geo.crs import wgs84_to_utm30

        # Two raw cells for Red A (MNC 7) very close to each other (~30m apart)
        # in central Jaén (lon ~ -3.7900, lat ~ 37.7700)
        cell1 = RawCellRecord(
            mcc=214,
            mnc=7,
            cell_id="CELL_A1",
            radio="LTE",
            lon=-3.79000,
            lat=37.77000,
        )
        cell2 = RawCellRecord(
            mcc=214,
            mnc=7,
            cell_id="CELL_A2",
            radio="NR",
            lon=-3.79020,
            lat=37.77010,
        )

        # OSM mast situated ~40m away from the cells (within snap radius 75m)
        mast_lon = -3.78980
        mast_lat= 37.77020
        mast = OsmMastRecord(
            osm_id="MAST_1",
            lon=mast_lon,
            lat=mast_lat,
            mast_type="communications_tower",
        )

        sites = cluster_opencellid_and_snap_osm(
            cells=[cell1, cell2],
            masts=[mast],
            cluster_radius_m=120.0,
            osm_snap_radius_m=75.0,
        )

        assert len(sites) == 1
        site = sites[0]
        assert site.network_alias == "Red A"
        assert site.source == DataSourceOrigin.ESTIMATED

        # Coordinates must have snapped to exact OSM mast coordinates in EPSG:25830
        expected_x, expected_y = wgs84_to_utm30(mast_lon, mast_lat)
        assert math.isclose(site.x_m, expected_x, abs_tol=1e-3)
        assert math.isclose(site.y_m, expected_y, abs_tol=1e-3)

        # Check sectors and bands: must configure n28 and n78
        bands_present = {
            cell.band.n_band
            for sector in site.sectors
            for cell in sector.cells
        }
        assert 28 in bands_present
        assert 78 in bands_present

    def test_clustering_without_osm_snap_when_beyond_radius(self):
        from ran_city.data_sources.opencellid_osm import (
            OsmMastRecord,
            RawCellRecord,
            cluster_opencellid_and_snap_osm,
        )
        from ran_city.geo.crs import wgs84_to_utm30

        cell = RawCellRecord(
            mcc=214,
            mnc=1,
            cell_id="CELL_B1",
            radio="NR",
            lon=-3.79000,
            lat=37.77000,
        )
        # Mast is ~500m away (well beyond 75m snap radius)
        far_mast = OsmMastRecord(
            osm_id="MAST_FAR",
            lon=-3.78400,
            lat=37.77000,
            mast_type="mast",
        )
        sites = cluster_opencellid_and_snap_osm(
            cells=[cell],
            masts=[far_mast],
            cluster_radius_m=120.0,
            osm_snap_radius_m=75.0,
        )
        assert len(sites) == 1
        expected_x, expected_y = wgs84_to_utm30(cell.lon, cell.lat)
        assert math.isclose(sites[0].x_m, expected_x, abs_tol=1e-3)
        assert math.isclose(sites[0].y_m, expected_y, abs_tol=1e-3)


class TestJaenCityScenario:
    """Tests for loading data/cities/jaen.yaml and running an end-to-end multi-cell simulation."""

    def test_load_real_jaen_yaml_and_schema(self):
        from ran_city.data_sources.city_schema import load_city_scenario

        yaml_path = Path("data/cities/jaen.yaml")
        assert yaml_path.is_file(), f"City scenario YAML not found at {yaml_path}"

        scenario = load_city_scenario(yaml_path)

        # Verify Bounding Box
        cfg = scenario.config
        assert len(cfg.bbox_wgs84) == 4
        assert len(cfg.bbox_utm30) == 4
        # Jaen BBox in UTM30N
        min_x, min_y, max_x, max_y = cfg.bbox_utm30
        assert 420_000.0 < min_x < max_x < 440_000.0
        assert 4_170_000.0 < min_y < max_y < 4_190_000.0

        # Verify Environments / Zones
        env_names = {z.environment.value for z in cfg.zones}
        assert "dense_urban" in env_names
        assert "urban" in env_names
        assert "rural" in env_names

        # Verify Operators and CNAF Spectrum
        op_aliases = {op.network_alias for op in cfg.operators}
        assert {"Red A", "Red B", "Red C"}.issubset(op_aliases)

        # Verify Sites
        assert len(scenario.sites) >= 9, f"Expected >= 9 sites, got {len(scenario.sites)}"
        operators_in_sites = {s.network_alias for s in scenario.sites}
        assert {"Red A", "Red B", "Red C"}.issubset(operators_in_sites)

        for site in scenario.sites:
            assert site.source == DataSourceOrigin.ESTIMATED
            # Every site must lie strictly inside the Jaén UTM30 bounding box
            assert min_x <= site.x_m <= max_x, (
                f"Site {site.site_id} x_m={site.x_m} outside bbox [{min_x}, {max_x}]"
            )
            assert min_y <= site.y_m <= max_y, (
                f"Site {site.site_id} y_m={site.y_m} outside bbox [{min_y}, {max_y}]"
            )
            # Realistic elevations for Jaen (between ~410m and ~820m, e.g. Los Olivares to Santa Catalina)
            assert 405.0 <= site.ground_z_m <= 820.0, (
                f"Site {site.site_id} has unrealistic elevation {site.ground_z_m} m"
            )

        elevations = [s.ground_z_m for s in scenario.sites]
        # Verify topographic relief span: low northern valley (< 460 m) and high southern hills (> 650 m)
        assert min(elevations) < 460.0
        assert max(elevations) > 650.0

    def test_jaen_scenario_simulation_rsrp_and_sinr(self):
        from ran_city.data_sources.city_schema import load_city_scenario

        yaml_path = Path("data/cities/jaen.yaml")
        scenario = load_city_scenario(yaml_path)

        # Create a test grid over central Jaén (e.g. 500m x 500m in urban resolution 12m)
        center_x = 430_380.0
        center_y = 4_180_400.0
        grid = ScenarioGrid.from_bounds(
            x_min=center_x - 300.0,
            y_min=center_y - 300.0,
            x_max=center_x + 300.0,
            y_max=center_y + 300.0,
            environment=EnvironmentType.URBAN,
            ground_z_m=530.0,
        )

        # Run coverage simulation across all 3 operators (Red A, Red B, Red C) and bands (n28, n78)
        for alias in ("Red A", "Red B", "Red C"):
            for band_num in (28, 78):
                res = compute_scenario_coverage(
                    sites=scenario.sites,
                    grid=grid,
                    network_alias=alias,
                    n_band=band_num,
                    cell_load_factor=1.0,
                )

                assert res.serving_rsrp_dbm.shape == grid.shape
                assert res.sinr_db.shape == grid.shape
                assert np.all(np.isfinite(res.serving_rsrp_dbm))
                assert np.all(np.isfinite(res.sinr_db))

                # Serving RSRP should be within realistic cellular values (e.g. -145 to -30 dBm)
                assert np.all(res.serving_rsrp_dbm >= -145.0)
                assert np.all(res.serving_rsrp_dbm <= -30.0)

                # SINR should be finite and bounded by SNR
                snr_db = res.serving_rsrp_dbm - res.noise_per_re_dbm
                assert np.all(res.sinr_db <= snr_db + 1e-6)
