"""Tests for coverage matrices, power per RE, decoupling, and trisector best server."""

import math

import numpy as np
import pytest
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
    BOLTZMANN_K_J_K,
    ScenarioCoverageResult,
    compute_cell_coverage,
    compute_scenario_coverage,
    power_per_re_dbm,
    re_thermal_noise_dbm,
    thermal_noise_dbm,
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
        cov_0 = compute_cell_coverage(
            cell_0, sector_azimuth_deg=0.0, grid_geom=geom, prop_matrix=prop
        )

        # Propagation matrix was NOT mutated
        assert np.array_equal(prop.loss_db, original_loss)

        # Recalculate with new electrical tilt = 8° WITHOUT recomputing prop_matrix!
        ant_tilt = AntennaConfig(
            n_rows=8, n_cols=8, mechanical_tilt_deg=0.0, electrical_tilt_deg=8.0
        )
        cell_tilt = Cell(
            cell_id="C_tilt",
            cell_type=CellType.MACRO,
            band=band,
            antenna=ant_tilt,
            tx_power_dbm=43.0,
            source=DataSourceOrigin.SYNTHETIC,
        )
        cov_tilt = compute_cell_coverage(
            cell_tilt, sector_azimuth_deg=0.0, grid_geom=geom, prop_matrix=prop
        )

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
            cells=(
                Cell(
                    cell_id="C0",
                    cell_type=CellType.MACRO,
                    band=band,
                    antenna=ant,
                    tx_power_dbm=43.0,
                    source=DataSourceOrigin.SYNTHETIC,
                ),
            ),
        )
        sec_120 = Sector(
            sector_id="S120",
            azimuth_deg=120.0,
            ant_height_m=25.0,
            cells=(
                Cell(
                    cell_id="C120",
                    cell_type=CellType.MACRO,
                    band=band,
                    antenna=ant,
                    tx_power_dbm=43.0,
                    source=DataSourceOrigin.SYNTHETIC,
                ),
            ),
        )
        sec_240 = Sector(
            sector_id="S240",
            azimuth_deg=240.0,
            ant_height_m=25.0,
            cells=(
                Cell(
                    cell_id="C240",
                    cell_type=CellType.MACRO,
                    band=band,
                    antenna=ant,
                    tx_power_dbm=43.0,
                    source=DataSourceOrigin.SYNTHETIC,
                ),
            ),
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
        grid_ref = ScenarioGrid.from_bounds(
            site_x + dx_0 - 6.0,
            site_y + dy_0 - 6.0,
            site_x + dx_0 + 6.0,
            site_y + dy_0 + 6.0,
            EnvironmentType.URBAN,
        )
        # Rotated scenario
        grid_rot = ScenarioGrid.from_bounds(
            site_x + dx_rot - 6.0,
            site_y + dy_rot - 6.0,
            site_x + dx_rot + 6.0,
            site_y + dy_rot + 6.0,
            EnvironmentType.URBAN,
        )

        band = NrBand.n78()
        ant = AntennaConfig(n_rows=4, n_cols=4, mechanical_tilt_deg=5.0)

        sec_ref = Sector(
            sector_id="S_REF",
            azimuth_deg=30.0,
            ant_height_m=25.0,
            cells=(
                Cell(
                    cell_id="CREF",
                    cell_type=CellType.MACRO,
                    band=band,
                    antenna=ant,
                    tx_power_dbm=43.0,
                    source=DataSourceOrigin.SYNTHETIC,
                ),
            ),
        )
        site_ref = Site(
            site_id="SITEREF",
            network_alias="A",
            x_m=site_x,
            y_m=site_y,
            sectors=(sec_ref,),
            source=DataSourceOrigin.SYNTHETIC,
        )

        sec_rot = Sector(
            sector_id="S_ROT",
            azimuth_deg=30.0 + rot_deg,
            ant_height_m=25.0,
            cells=(
                Cell(
                    cell_id="CROT",
                    cell_type=CellType.MACRO,
                    band=band,
                    antenna=ant,
                    tx_power_dbm=43.0,
                    source=DataSourceOrigin.SYNTHETIC,
                ),
            ),
        )
        site_rot = Site(
            site_id="SITEROT",
            network_alias="A",
            x_m=site_x,
            y_m=site_y,
            sectors=(sec_rot,),
            source=DataSourceOrigin.SYNTHETIC,
        )

        cov_ref = compute_scenario_coverage([site_ref], grid=grid_ref, los_mask_override=True)
        cov_rot = compute_scenario_coverage([site_rot], grid=grid_rot, los_mask_override=True)

        assert math.isclose(
            cov_ref.serving_rsrp_dbm[0, 0], cov_rot.serving_rsrp_dbm[0, 0], abs_tol=1e-5
        )


class TestThermalNoise:
    """Tests for thermal noise k_B * T * B * F per Resource Element and channel (3GPP TS 38.101-1 / TS 38.104)."""

    def test_thermal_noise_analytical_exact(self):
        # Boltzmann constant (1.380649e-23 J/K, SI 2019 exact) yielding -173.97519 dBm/Hz at 290 K
        assert math.isclose(BOLTZMANN_K_J_K, 1.380649e-23, rel_tol=1e-9)

        # Reference values at T=290 K, F=9 dB with tolerance < 1e-4 dB (CA-2):
        # n28 (15 kHz SCS): -123.21427 dBm
        n_n28 = re_thermal_noise_dbm(NrBand.n28(), noise_figure_db=9.0, temperature_k=290.0)
        assert isinstance(n_n28, Dbm)
        assert math.isclose(n_n28.value, -123.21427, abs_tol=1e-4)

        # n78 (30 kHz SCS): -120.20397 dBm
        n_n78 = re_thermal_noise_dbm(NrBand.n78(), noise_figure_db=9.0, temperature_k=290.0)
        assert isinstance(n_n78, Dbm)
        assert math.isclose(n_n78.value, -120.20397, abs_tol=1e-4)

        # n258 (120 kHz SCS): -114.18337 dBm
        n_n258 = re_thermal_noise_dbm(NrBand.n258(), noise_figure_db=9.0, temperature_k=290.0)
        assert isinstance(n_n258, Dbm)
        assert math.isclose(n_n258.value, -114.18337, abs_tol=1e-4)

        # Full channel thermal noise vs per-RE thermal noise (12 * N_RB subcarriers)
        band_78 = NrBand.n78()  # 273 RBs * 12 = 3276 subcarriers * 30 kHz = 98.28 MHz
        n_ch_78 = thermal_noise_dbm(
            bandwidth_hz=12.0 * band_78.num_rbs * band_78.scs_khz * 1000.0,
            noise_figure_db=9.0,
            temperature_k=290.0,
        )
        assert math.isclose(
            n_ch_78.value,
            n_n78.value + 10.0 * math.log10(12.0 * band_78.num_rbs),
            abs_tol=1e-6,
        )

    def test_thermal_noise_bandwidth_scaling(self):
        # Doubling bandwidth must increase noise by 10*log10(2) = 3.0103 dB
        n1 = thermal_noise_dbm(bandwidth_hz=15000.0, noise_figure_db=9.0, temperature_k=290.0)
        n2 = thermal_noise_dbm(bandwidth_hz=30000.0, noise_figure_db=9.0, temperature_k=290.0)
        diff = n2.value - n1.value
        assert math.isclose(diff, 10.0 * math.log10(2.0), abs_tol=1e-5)
        assert math.isclose(diff, 3.0103, abs_tol=1e-4)


class TestSinrAndInterference:
    """Tests for co-channel interference in linear mW, SINR, network/band isolation, and invariants."""

    def test_single_cell_sinr_equals_snr(self):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.URBAN)
        ant = AntennaConfig(n_rows=4, n_cols=4)
        band = NrBand.n78()
        sec = Sector(
            sector_id="S0",
            azimuth_deg=0.0,
            ant_height_m=25.0,
            cells=(
                Cell(
                    cell_id="C0",
                    cell_type=CellType.MACRO,
                    band=band,
                    antenna=ant,
                    tx_power_dbm=43.0,
                    source=DataSourceOrigin.SYNTHETIC,
                ),
            ),
        )
        site = Site(
            site_id="SITE0",
            network_alias="Red A",
            x_m=50.0,
            y_m=50.0,
            sectors=(sec,),
            source=DataSourceOrigin.SYNTHETIC,
        )

        res = compute_scenario_coverage([site], grid=grid, los_mask_override=True)
        assert hasattr(res, "interference_mw")
        assert hasattr(res, "sinr_db")
        assert hasattr(res, "noise_per_re_dbm")

        # Single active cell: interference is strictly 0.0 mW
        assert np.all(res.interference_mw == 0.0)
        # SINR equals SNR = serving_rsrp_dbm - noise_per_re_dbm
        expected_snr = res.serving_rsrp_dbm - res.noise_per_re_dbm
        np.testing.assert_allclose(res.sinr_db, expected_snr, rtol=1e-5, atol=1e-5)

    def test_symmetric_sites_sinr_theoretical_values(self):
        # 1-pixel grid at (500, 500)
        grid = ScenarioGrid.from_bounds(494.0, 494.0, 506.0, 506.0, EnvironmentType.URBAN)
        band = NrBand.n78()
        ant = AntennaConfig(n_rows=4, n_cols=4, mechanical_tilt_deg=0.0)

        # 2 opposing equidistant sites at (500, 600) and (500, 400), 100 m from (500, 500)
        site_north = Site(
            site_id="SITE_N",
            network_alias="Red A",
            x_m=500.0,
            y_m=600.0,
            sectors=(
                Sector(
                    sector_id="S_N",
                    azimuth_deg=180.0,
                    ant_height_m=1.5,
                    cells=(
                        Cell(
                            cell_id="C_N",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )
        site_south = Site(
            site_id="SITE_S",
            network_alias="Red A",
            x_m=500.0,
            y_m=400.0,
            sectors=(
                Sector(
                    sector_id="S_S",
                    azimuth_deg=0.0,
                    ant_height_m=1.5,
                    cells=(
                        Cell(
                            cell_id="C_S",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )

        res_2 = compute_scenario_coverage(
            [site_north, site_south],
            grid=grid,
            los_mask_override=True,
            cell_load_factor=1.0,
        )
        # 2 identical equidistant servers: S / (S + N) approx 1.0 -> 0.0 dB
        assert math.isclose(res_2.sinr_db[0, 0], 0.0, abs_tol=0.01)

        # 3 equidistant sites at 120° angles around (500, 500) at 100 m
        r = 100.0
        # Angle 0 (North): (500, 600), pointing 180°
        # Angle 120 (Southeast): (500 + r*sin(120°), 500 + r*cos(120°)) = (586.6025, 450), pointing (120 + 180) % 360 = 300°
        # Angle 240 (Southwest): (500 + r*sin(240°), 500 + r*cos(240°)) = (413.3975, 450), pointing (240 + 180) % 360 = 60°
        site_1 = site_north
        site_2 = Site(
            site_id="SITE_SE",
            network_alias="Red A",
            x_m=500.0 + r * math.sin(math.radians(120.0)),
            y_m=500.0 + r * math.cos(math.radians(120.0)),
            sectors=(
                Sector(
                    sector_id="S_SE",
                    azimuth_deg=300.0,
                    ant_height_m=1.5,
                    cells=(
                        Cell(
                            cell_id="C_SE",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )
        site_3 = Site(
            site_id="SITE_SW",
            network_alias="Red A",
            x_m=500.0 + r * math.sin(math.radians(240.0)),
            y_m=500.0 + r * math.cos(math.radians(240.0)),
            sectors=(
                Sector(
                    sector_id="S_SW",
                    azimuth_deg=60.0,
                    ant_height_m=1.5,
                    cells=(
                        Cell(
                            cell_id="C_SW",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )

        res_3 = compute_scenario_coverage(
            [site_1, site_2, site_3],
            grid=grid,
            los_mask_override=True,
            cell_load_factor=1.0,
        )
        # 3 identical equidistant servers: S / (2S + N) approx 0.5 -> -10*log10(2) approx -3.0103 dB
        expected_sinr_3 = -10.0 * math.log10(2.0)
        assert math.isclose(res_3.sinr_db[0, 0], expected_sinr_3, abs_tol=0.01)

        # CA-7: Turning on additional co-channel interfering cells strictly reduces SINR
        res_1 = compute_scenario_coverage([site_1], grid=grid, los_mask_override=True)
        assert res_1.sinr_db[0, 0] > res_2.sinr_db[0, 0] > res_3.sinr_db[0, 0]

        # When cell_load_factor == 0.0, multi-cell interference is 0.0 mW and SINR == SNR
        res_zero_load = compute_scenario_coverage(
            [site_1, site_2, site_3],
            grid=grid,
            los_mask_override=True,
            cell_load_factor=0.0,
        )
        assert res_zero_load.interference_mw[0, 0] == 0.0
        assert math.isclose(
            res_zero_load.sinr_db[0, 0],
            res_zero_load.serving_rsrp_dbm[0, 0] - res_zero_load.noise_per_re_dbm,
            abs_tol=1e-6,
        )

        # Out-of-bounds cell_load_factor raises ValueError
        with pytest.raises(ValueError, match="cell_load_factor"):
            compute_scenario_coverage([site_1], grid=grid, cell_load_factor=-0.1)
        with pytest.raises(ValueError, match="cell_load_factor"):
            compute_scenario_coverage([site_1], grid=grid, cell_load_factor=1.1)

    def test_cochannel_filtering_and_cross_network_error(self):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.URBAN)
        ant = AntennaConfig(n_rows=4, n_cols=4)
        band_78 = NrBand.n78()
        band_28 = NrBand.n28()

        site_a_78 = Site(
            site_id="SITE_A_78",
            network_alias="Red A",
            x_m=20.0,
            y_m=50.0,
            sectors=(
                Sector(
                    sector_id="S_A_78",
                    azimuth_deg=0.0,
                    ant_height_m=25.0,
                    cells=(
                        Cell(
                            cell_id="C_A_78",
                            cell_type=CellType.MACRO,
                            band=band_78,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )
        site_b_78 = Site(
            site_id="SITE_B_78",
            network_alias="Red B",
            x_m=80.0,
            y_m=50.0,
            sectors=(
                Sector(
                    sector_id="S_B_78",
                    azimuth_deg=180.0,
                    ant_height_m=25.0,
                    cells=(
                        Cell(
                            cell_id="C_B_78",
                            cell_type=CellType.MACRO,
                            band=band_78,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )
        site_a_28 = Site(
            site_id="SITE_A_28",
            network_alias="Red A",
            x_m=50.0,
            y_m=80.0,
            sectors=(
                Sector(
                    sector_id="S_A_28",
                    azimuth_deg=90.0,
                    ant_height_m=25.0,
                    cells=(
                        Cell(
                            cell_id="C_A_28",
                            cell_type=CellType.MACRO,
                            band=band_28,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )

        all_sites = [site_a_78, site_b_78, site_a_28]

        # 1. Calling without filters with mixed networks/bands must raise ValueError
        with pytest.raises(ValueError, match="co-channel"):
            compute_scenario_coverage(all_sites, grid=grid)

        # 2. Calling with network_alias="Red A" but no band filter leaves mixed bands (n78 and n28) -> ValueError
        with pytest.raises(ValueError, match="co-channel"):
            compute_scenario_coverage(all_sites, grid=grid, network_alias="Red A")

        # 3. Calling with n_band=78 but no network filter leaves mixed networks ("Red A" and "Red B") -> ValueError
        with pytest.raises(ValueError, match="co-channel"):
            compute_scenario_coverage(all_sites, grid=grid, n_band=78)

        # 4. Correctly isolated layer: network_alias="Red A" and n_band=78 -> succeeds
        res_isolated = compute_scenario_coverage(
            all_sites, grid=grid, network_alias="Red A", n_band=78
        )
        assert res_isolated.cell_ids == ("C_A_78",)

    @given(
        eta1=st.floats(min_value=0.0, max_value=1.0),
        eta2=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_sinr_load_factor_monotonicity_hypothesis(self, eta1, eta2):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.URBAN)
        ant = AntennaConfig(n_rows=4, n_cols=4)
        band = NrBand.n78()

        site1 = Site(
            site_id="S1",
            network_alias="Red A",
            x_m=30.0,
            y_m=50.0,
            sectors=(
                Sector(
                    sector_id="SEC1",
                    azimuth_deg=90.0,
                    ant_height_m=25.0,
                    cells=(
                        Cell(
                            cell_id="C1",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )
        site2 = Site(
            site_id="S2",
            network_alias="Red A",
            x_m=70.0,
            y_m=50.0,
            sectors=(
                Sector(
                    sector_id="SEC2",
                    azimuth_deg=270.0,
                    ant_height_m=25.0,
                    cells=(
                        Cell(
                            cell_id="C2",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )

        min_eta, max_eta = sorted([eta1, eta2])
        res_min = compute_scenario_coverage(
            [site1, site2], grid=grid, los_mask_override=True, cell_load_factor=min_eta
        )
        res_max = compute_scenario_coverage(
            [site1, site2], grid=grid, los_mask_override=True, cell_load_factor=max_eta
        )

        # Higher load factor means higher interference, so lower or equal SINR
        assert np.all(res_min.sinr_db >= res_max.sinr_db - 1e-9)

    @given(eta=st.floats(min_value=0.0, max_value=1.0))
    def test_sinr_bounded_by_snr_hypothesis(self, eta):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.URBAN)
        ant = AntennaConfig(n_rows=4, n_cols=4)
        band = NrBand.n78()

        site1 = Site(
            site_id="S1",
            network_alias="Red A",
            x_m=30.0,
            y_m=50.0,
            sectors=(
                Sector(
                    sector_id="SEC1",
                    azimuth_deg=90.0,
                    ant_height_m=25.0,
                    cells=(
                        Cell(
                            cell_id="C1",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )
        site2 = Site(
            site_id="S2",
            network_alias="Red A",
            x_m=70.0,
            y_m=50.0,
            sectors=(
                Sector(
                    sector_id="SEC2",
                    azimuth_deg=270.0,
                    ant_height_m=25.0,
                    cells=(
                        Cell(
                            cell_id="C2",
                            cell_type=CellType.MACRO,
                            band=band,
                            antenna=ant,
                            tx_power_dbm=43.0,
                            source=DataSourceOrigin.SYNTHETIC,
                        ),
                    ),
                ),
            ),
            source=DataSourceOrigin.SYNTHETIC,
        )

        res = compute_scenario_coverage(
            [site1, site2], grid=grid, los_mask_override=True, cell_load_factor=eta
        )
        snr_db = res.serving_rsrp_dbm - res.noise_per_re_dbm
        # SINR <= SNR always
        assert np.all(res.sinr_db <= snr_db + 1e-9)
