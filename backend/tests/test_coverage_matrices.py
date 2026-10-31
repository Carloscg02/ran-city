"""Tests for coverage matrices, power per RE, decoupling, and trisector best server."""

import math

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from ran_city.antenna.tr38901 import AntennaConfig
from ran_city.domain.grid import EnvironmentType, ScenarioGrid
from ran_city.domain.models import (
    Cell,
    CellType,
    DataSourceOrigin,
    NrBand,
    Sector,
    Site,
)
from ran_city.domain.units import Dbm, Point3D
from ran_city.radio.coverage import (
    ScenarioCoverageResult,
    compute_cell_coverage,
    compute_scenario_coverage,
    power_per_re_dbm,
)
from ran_city.radio.tr38901 import compute_propagation_matrix


class TestPowerPerResourceElement:
    """Tests for 3GPP TS 38.215 / TS 38.211 power per RE calculation."""

    def test_power_per_re_exact(self):
        # 43 dBm total power, 273 RBs (n78 100 MHz, 30 kHz SCS)
        # 43 - 10*log10(12 * 273) = 43 - 10*log10(3276) = 7.84656 dBm
        p_re = power_per_re_dbm(43.0, 273)
        assert isinstance(p_re, Dbm)
        expected = 43.0 - 10.0 * math.log10(12.0 * 273.0)
        assert math.isclose(p_re.value, expected, abs_tol=1e-5)
        assert math.isclose(p_re.value, 7.84656, abs_tol=1e-4)


class TestCoverageDecouplingAndTrisector:
    """Tests for matrix decoupling and multicell scenario coverage."""

    def test_antenna_propagation_matrix_decoupling(self):
        # Grid and geometry
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 200.0, 200.0, EnvironmentType.URBAN)
        tx = Point3D(100.0, 100.0, 25.0)
        geom = grid.geometry_from_tx(tx)

        # Baseline propagation matrix precomputed
        prop = compute_propagation_matrix(
            CellType.MACRO, freq_ghz=3.5, h_bs_m=25.0, h_ut_m=1.5, grid_geom=geom, seed=42
        )
        original_loss = np.copy(prop.loss_db)

        # Cell with initial tilt = 0°
        band = NrBand.n78()
        ant_0 = AntennaConfig(n_rows=8, n_cols=8, mechanical_tilt_deg=0.0, electrical_tilt_deg=0.0)
        cell_0 = Cell(
            cell_id="C0",
            cell_type=CellType.MACRO,
            band=band,
            antenna=ant_0,
            tx_power_dbm=43.0,
            source=DataSourceOrigin.SYNTHETIC,
        )
        cov_0 = compute_cell_coverage(cell_0, sector_azimuth_deg=0.0, grid_geom=geom, prop_matrix=prop)

        # Propagation matrix was NOT mutated
        assert np.array_equal(prop.loss_db, original_loss)

        # Recalculate with new electrical tilt = 8° WITHOUT recomputing prop_matrix!
        ant_tilt = AntennaConfig(n_rows=8, n_cols=8, mechanical_tilt_deg=0.0, electrical_tilt_deg=8.0)
        cell_tilt = Cell(
            cell_id="C_tilt",
            cell_type=CellType.MACRO,
            band=band,
            antenna=ant_tilt,
            tx_power_dbm=43.0,
            source=DataSourceOrigin.SYNTHETIC,
        )
        cov_tilt = compute_cell_coverage(cell_tilt, sector_azimuth_deg=0.0, grid_geom=geom, prop_matrix=prop)

        # Still not mutated
        assert np.array_equal(prop.loss_db, original_loss)
        # Antenna gains and RSRP have changed due to tilt
        assert not np.array_equal(cov_0.antenna_gain_dbi, cov_tilt.antenna_gain_dbi)
        assert not np.array_equal(cov_0.rsrp_dbm, cov_tilt.rsrp_dbm)

    def test_trisector_best_server_partition(self):
        # 1 km x 1 km grid centered at (500, 500)
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 1000.0, 1000.0, EnvironmentType.URBAN)
        site_x, site_y = 500.0, 500.0
        band = NrBand.n78()
        ant = AntennaConfig(n_rows=8, n_cols=8, mechanical_tilt_deg=4.0)

        # Trisector site: 0° (North), 120° (Southeast), 240° (Southwest)
        sec_0 = Sector(
            sector_id="S0",
            azimuth_deg=0.0,
            ant_height_m=25.0,
            cells=(Cell(cell_id="C0", cell_type=CellType.MACRO, band=band, antenna=ant, tx_power_dbm=43.0, source=DataSourceOrigin.SYNTHETIC),),
        )
        sec_120 = Sector(
            sector_id="S120",
            azimuth_deg=120.0,
            ant_height_m=25.0,
            cells=(Cell(cell_id="C120", cell_type=CellType.MACRO, band=band, antenna=ant, tx_power_dbm=43.0, source=DataSourceOrigin.SYNTHETIC),),
        )
        sec_240 = Sector(
            sector_id="S240",
            azimuth_deg=240.0,
            ant_height_m=25.0,
            cells=(Cell(cell_id="C240", cell_type=CellType.MACRO, band=band, antenna=ant, tx_power_dbm=43.0, source=DataSourceOrigin.SYNTHETIC),),
        )

        site = Site(
            site_id="SITE_TRI",
            network_alias="Red A",
            x_m=site_x,
            y_m=site_y,
            ground_z_m=0.0,
            sectors=(sec_0, sec_120, sec_240),
            source=DataSourceOrigin.SYNTHETIC,
        )

        res = compute_scenario_coverage([site], grid=grid, los_mask_override=True)
        assert isinstance(res, ScenarioCoverageResult)
        assert res.cell_ids == ("C0", "C120", "C240")
        assert res.best_server_idx.shape == grid.shape
        assert res.serving_rsrp_dbm.shape == grid.shape

        # Verify dominant directions:
        # 1. Pixel directly North of site: dx = 0, dy = +200 -> (500, 700)
        idx_north_x = np.argmin(np.abs(grid.xs - 500.0))
        idx_north_y = np.argmin(np.abs(grid.ys - 700.0))
        assert res.best_server_idx[idx_north_y, idx_north_x] == 0  # Sector 0°

        # 2. Pixel Southeast of site (azimuth ~ 120°): dx = 200*sin(120°) = 173.2, dy = 200*cos(120°) = -100
        idx_se_x = np.argmin(np.abs(grid.xs - (500.0 + 173.2)))
        idx_se_y = np.argmin(np.abs(grid.ys - (500.0 - 100.0)))
        assert res.best_server_idx[idx_se_y, idx_se_x] == 1  # Sector 120°

        # 3. Pixel Southwest of site (azimuth ~ 240°): dx = 200*sin(240°) = -173.2, dy = 200*cos(240°) = -100
        idx_sw_x = np.argmin(np.abs(grid.xs - (500.0 - 173.2)))
        idx_sw_y = np.argmin(np.abs(grid.ys - (500.0 - 100.0)))
        assert res.best_server_idx[idx_sw_y, idx_sw_x] == 2  # Sector 240°

    @given(rot_deg=st.sampled_from([0.0, 90.0, 180.0, 270.0]))
    def test_rotational_invariance_hypothesis(self, rot_deg):
        # A single pixel at (dx, dy) = (50, 100) from site at (500, 500)
        # Rotating sector azimuth by +rot_deg and rotating (dx, dy) by the same +rot_deg clockwise
        # must yield identical RSRP
        dx_0, dy_0 = 50.0, 100.0
        rad = math.radians(rot_deg)
        dx_rot = dx_0 * math.cos(rad) + dy_0 * math.sin(rad)
        dy_rot = -dx_0 * math.sin(rad) + dy_0 * math.cos(rad)

        site_x, site_y = 500.0, 500.0
        # Reference scenario (rot=0)
        grid_ref = ScenarioGrid.from_bounds(site_x + dx_0 - 6.0, site_y + dy_0 - 6.0, site_x + dx_0 + 6.0, site_y + dy_0 + 6.0, EnvironmentType.URBAN)
        # Rotated scenario
        grid_rot = ScenarioGrid.from_bounds(site_x + dx_rot - 6.0, site_y + dy_rot - 6.0, site_x + dx_rot + 6.0, site_y + dy_rot + 6.0, EnvironmentType.URBAN)

        band = NrBand.n78()
        ant = AntennaConfig(n_rows=4, n_cols=4, mechanical_tilt_deg=5.0)

        sec_ref = Sector(
            sector_id="S_REF",
            azimuth_deg=30.0,
            ant_height_m=25.0,
            cells=(Cell(cell_id="CREF", cell_type=CellType.MACRO, band=band, antenna=ant, tx_power_dbm=43.0, source=DataSourceOrigin.SYNTHETIC),),
        )
        site_ref = Site(site_id="SITEREF", network_alias="A", x_m=site_x, y_m=site_y, sectors=(sec_ref,), source=DataSourceOrigin.SYNTHETIC)

        sec_rot = Sector(
            sector_id="S_ROT",
            azimuth_deg=30.0 + rot_deg,
            ant_height_m=25.0,
            cells=(Cell(cell_id="CROT", cell_type=CellType.MACRO, band=band, antenna=ant, tx_power_dbm=43.0, source=DataSourceOrigin.SYNTHETIC),),
        )
        site_rot = Site(site_id="SITEROT", network_alias="A", x_m=site_x, y_m=site_y, sectors=(sec_rot,), source=DataSourceOrigin.SYNTHETIC)

        cov_ref = compute_scenario_coverage([site_ref], grid=grid_ref, los_mask_override=True)
        cov_rot = compute_scenario_coverage([site_rot], grid=grid_rot, los_mask_override=True)

        assert math.isclose(cov_ref.serving_rsrp_dbm[0, 0], cov_rot.serving_rsrp_dbm[0, 0], abs_tol=1e-5)
