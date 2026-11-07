"""Tests for 3GPP TR 38.901 propagation models (Pr_LOS, UMa, UMi, calibration)."""

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ran_city.domain.grid import EnvironmentType, ScenarioGrid
from ran_city.domain.models import CellType
from ran_city.domain.units import Point3D
from ran_city.radio.tr38901 import (
    CalibrationParams,
    PropagationMatrix,
    compute_propagation_matrix,
    decorrelation_distance_m,
    los_probability,
    sample_los_mask,
    sample_shadow_fading_map,
    shadow_fading_std_db,
)


class TestLosProbability:
    """Tests for LOS probability formula (3GPP TR 38.901 Table 7.4.2-1)."""

    def test_los_probability_under_18m(self):
        # Under or equal to 18 meters, Pr_LOS is strictly 1.0 for all environments
        assert los_probability(0.0, CellType.MACRO) == 1.0
        assert los_probability(10.0, CellType.MICRO) == 1.0
        assert los_probability(18.0, CellType.MACRO) == 1.0
        assert los_probability(18.0, CellType.PICO) == 1.0

    def test_los_probability_analytical_values(self):
        # UMi at 100 m
        # 18/100 + exp(-100/36)*(1 - 18/100) = 0.18 + exp(-2.777778)*0.82 = 0.230985
        pr_umi_100 = los_probability(100.0, CellType.MICRO, h_ut_m=1.5)
        assert math.isclose(pr_umi_100, 0.230985, abs_tol=1e-5)

        # UMa at 100 m, h_ut = 1.5 m (c_prime = 0)
        # 18/100 + exp(-100/63)*(1 - 18/100) = 0.18 + exp(-1.5873)*0.82 = 0.347668
        pr_uma_100 = los_probability(100.0, CellType.MACRO, h_ut_m=1.5)
        assert math.isclose(pr_uma_100, 0.347668, abs_tol=1e-5)

        # UMa at 100 m with h_ut = 20.0 m (> 13 m, boost applies)
        pr_uma_100_high = los_probability(100.0, CellType.MACRO, h_ut_m=20.0)
        assert math.isclose(pr_uma_100_high, 0.47834, abs_tol=1e-4)

        # Higher BS or macro implies higher Pr_LOS than UMi street canyon at equal distance > 18 m
        assert pr_uma_100 > pr_umi_100

    def test_sample_los_mask_reproducibility(self):
        pr = np.full((10, 10), 0.5)
        mask1 = sample_los_mask(pr, seed=123)
        mask2 = sample_los_mask(pr, seed=123)
        mask3 = sample_los_mask(pr, seed=456)
        assert np.array_equal(mask1, mask2)
        assert not np.array_equal(mask1, mask3)

    @given(d2d=st.floats(min_value=0.0, max_value=5000.0))
    def test_pr_los_bounds_hypothesis(self, d2d):
        pr_macro = los_probability(d2d, CellType.MACRO, h_ut_m=1.5)
        pr_micro = los_probability(d2d, CellType.MICRO, h_ut_m=1.5)
        assert 0.0 <= pr_macro <= 1.0
        assert 0.0 <= pr_micro <= 1.0

    def test_pr_los_monotonic_decrease(self):
        distances = np.linspace(19.0, 1000.0, 50)
        pr_vals = [los_probability(d, CellType.MACRO, h_ut_m=1.5) for d in distances]
        assert all(pr_vals[i] >= pr_vals[i + 1] for i in range(len(pr_vals) - 1))


class TestPathLossTR38901:
    """Tests for UMa and UMi path loss formulas (3GPP TR 38.901 Table 7.4.1-1)."""

    def test_uma_analytical_values_before_and_after_breakpoint(self):
        # 3.5 GHz, h_bs=25 m, h_ut=1.5 m -> d_bp = 560.388 m
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 2000.0, 50.0, EnvironmentType.RURAL)
        tx = Point3D(0.0, 25.0, 25.0)
        geom = grid.geometry_from_tx(tx)

        # Before breakpoint: d2d = 100 m (LOS: 83.138 dB, NLOS: 103.038 dB)
        prop_los = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=3.5,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            los_mask=np.ones(grid.shape, dtype=bool),
        )
        assert isinstance(prop_los, PropagationMatrix)
        idx_100 = np.argmin(np.abs(geom.d2d_m[0] - 100.0))
        d3d_100 = geom.d3d_m[0, idx_100]
        expected_pl_los_100 = 28.0 + 22.0 * math.log10(d3d_100) + 20.0 * math.log10(3.5)
        assert math.isclose(prop_los.loss_db[0, idx_100], expected_pl_los_100, abs_tol=1e-4)

        # After breakpoint: pixel near 1000 m
        idx_1000 = np.argmin(np.abs(geom.d2d_m[0] - 1000.0))
        d3d_1000 = geom.d3d_m[0, idx_1000]
        h_bs_eff = 24.0
        h_ut_eff = 0.5
        d_bp = 4.0 * h_bs_eff * h_ut_eff * (3.5 * 1e9) / 299792458.0
        dh = 23.5
        expected_pl_los_1000 = (
            28.0
            + 40.0 * math.log10(d3d_1000)
            + 20.0 * math.log10(3.5)
            - 9.0 * math.log10(d_bp**2 + dh**2)
        )
        assert math.isclose(prop_los.loss_db[0, idx_1000], expected_pl_los_1000, abs_tol=1e-4)

        # NLOS:
        prop_nlos = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=3.5,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            los_mask=np.zeros(grid.shape, dtype=bool),
        )
        expected_pl_nlos_100 = 13.54 + 39.08 * math.log10(d3d_100) + 20.0 * math.log10(3.5)
        assert math.isclose(prop_nlos.loss_db[0, idx_100], expected_pl_nlos_100, abs_tol=1e-4)
        assert prop_nlos.loss_db[0, idx_100] > prop_los.loss_db[0, idx_100]

    def test_umi_analytical_values(self):
        # 3.5 GHz, h_bs=10 m, h_ut=1.5 m -> d_bp = 210.145 m
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 1000.0, 50.0, EnvironmentType.RURAL)
        tx = Point3D(0.0, 25.0, 10.0)
        geom = grid.geometry_from_tx(tx)

        prop_los = compute_propagation_matrix(
            CellType.MICRO,
            freq_ghz=3.5,
            h_bs_m=10.0,
            h_ut_m=1.5,
            grid_geom=geom,
            los_mask=np.ones(grid.shape, dtype=bool),
        )
        idx_100 = np.argmin(np.abs(geom.d2d_m[0] - 100.0))
        d3d_100 = geom.d3d_m[0, idx_100]
        expected_pl_umi_los_100 = 32.4 + 21.0 * math.log10(d3d_100) + 20.0 * math.log10(3.5)
        assert math.isclose(prop_los.loss_db[0, idx_100], expected_pl_umi_los_100, abs_tol=1e-4)

    def test_calibration_offset(self):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.URBAN)
        geom = grid.geometry_from_tx(Point3D(50.0, 50.0, 25.0))

        base_prop = compute_propagation_matrix(
            CellType.MACRO, freq_ghz=3.5, h_bs_m=25.0, h_ut_m=1.5, grid_geom=geom, seed=42
        )
        cal_prop = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=3.5,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            seed=42,
            calibration=CalibrationParams(offset_db=3.5),
        )
        diff = cal_prop.loss_db - base_prop.loss_db
        assert np.allclose(diff, 3.5, atol=1e-6)

    def test_monotonic_path_loss_with_distance(self):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 1000.0, 12.0, EnvironmentType.URBAN)
        geom = grid.geometry_from_tx(Point3D(0.0, 6.0, 25.0))
        prop_los = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=3.5,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            los_mask=np.ones(grid.shape, dtype=bool),
        )
        prop_nlos = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=3.5,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            los_mask=np.zeros(grid.shape, dtype=bool),
        )
        # Loss must increase monotonically along the row with distance
        losses_los = prop_los.loss_db[0]
        losses_nlos = prop_nlos.loss_db[0]
        assert np.all(np.diff(losses_los) >= 0.0)
        assert np.all(np.diff(losses_nlos) >= 0.0)

    @given(
        freq_ghz=st.floats(min_value=0.5, max_value=100.0),
        extent=st.floats(min_value=50.0, max_value=1000.0),
    )
    def test_nlos_greater_equal_los_hypothesis(self, freq_ghz, extent):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, extent, 50.0, EnvironmentType.DENSE_URBAN)
        geom = grid.geometry_from_tx(Point3D(0.0, 25.0, 25.0))
        prop_los = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=freq_ghz,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            los_mask=np.ones(grid.shape, dtype=bool),
        )
        prop_nlos = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=freq_ghz,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            los_mask=np.zeros(grid.shape, dtype=bool),
        )
        assert np.all(prop_nlos.loss_db >= prop_los.loss_db - 1e-9)


class TestShadowFadingTR38901:
    """Tests for 3GPP TR 38.901 log-normal correlated 2D shadow fading (Table 7.4.1-1 & Table 7.5-6)."""

    def test_shadow_fading_std_db_normative(self):
        # 3GPP TR 38.901 Table 7.4.1-1
        assert shadow_fading_std_db(CellType.MACRO, is_los=True) == 4.0
        assert shadow_fading_std_db(CellType.MACRO, is_los=False) == 6.0
        assert shadow_fading_std_db(CellType.MICRO, is_los=True) == 4.0
        assert shadow_fading_std_db(CellType.MICRO, is_los=False) == 8.2
        assert shadow_fading_std_db(CellType.PICO, is_los=True) == 4.0
        assert shadow_fading_std_db(CellType.PICO, is_los=False) == 8.2

    def test_decorrelation_distance_m_normative(self):
        # 3GPP TR 38.901 Table 7.5-6
        assert decorrelation_distance_m(CellType.MACRO, is_los=True) == 37.0
        assert decorrelation_distance_m(CellType.MACRO, is_los=False) == 50.0
        assert decorrelation_distance_m(CellType.MICRO, is_los=True) == 10.0
        assert decorrelation_distance_m(CellType.MICRO, is_los=False) == 13.0
        assert decorrelation_distance_m(CellType.PICO, is_los=True) == 10.0
        assert decorrelation_distance_m(CellType.PICO, is_los=False) == 13.0

    def test_sample_shadow_fading_map_reproducibility(self):
        los_mask = np.ones((50, 50), dtype=bool)
        sf1 = sample_shadow_fading_map(CellType.MACRO, los_mask, resolution_m=5.0, seed=42)
        sf2 = sample_shadow_fading_map(CellType.MACRO, los_mask, resolution_m=5.0, seed=42)
        sf3 = sample_shadow_fading_map(CellType.MACRO, los_mask, resolution_m=5.0, seed=99)

        assert np.array_equal(sf1, sf2)
        assert not np.array_equal(sf1, sf3)

    def test_sample_shadow_fading_map_statistics_and_correlation(self):
        # 120 x 120 grid with 5.0 m resolution
        los_mask = np.ones((120, 120), dtype=bool)
        sf_los = sample_shadow_fading_map(CellType.MACRO, los_mask, resolution_m=5.0, seed=9)

        # LOS: sigma_sf = 4.0 dB
        assert -0.5 <= float(np.mean(sf_los)) <= 0.5
        assert abs(float(np.std(sf_los)) - 4.0) <= 0.6

        # Spatial correlation between adjacent pixels along x
        corr_x_los = np.corrcoef(sf_los[:, :-1].ravel(), sf_los[:, 1:].ravel())[0, 1]
        assert corr_x_los > 0.7

        # NLOS: sigma_sf = 6.0 dB
        nlos_mask = np.zeros((120, 120), dtype=bool)
        sf_nlos = sample_shadow_fading_map(CellType.MACRO, nlos_mask, resolution_m=5.0, seed=9)
        assert -0.5 <= float(np.mean(sf_nlos)) <= 0.5
        assert abs(float(np.std(sf_nlos)) - 6.0) <= 0.6
        corr_x_nlos = np.corrcoef(sf_nlos[:, :-1].ravel(), sf_nlos[:, 1:].ravel())[0, 1]
        assert corr_x_nlos > 0.7

    def test_sample_shadow_fading_mixed_mask_and_boundary_unbiased_variance(self):
        # Mixed mask: top half LOS (sigma=4.0), bottom half NLOS (sigma=6.0) on a 20x20 grid
        mixed_mask = np.zeros((20, 20), dtype=bool)
        mixed_mask[:10, :] = True

        realizations = np.array(
            [
                sample_shadow_fading_map(CellType.MACRO, mixed_mask, resolution_m=5.0, seed=s)
                for s in range(400)
            ]
        )
        per_pixel_std = np.std(realizations, axis=0)

        # Verify corners and interior match normative std without boundary reflection inflation
        assert math.isclose(float(per_pixel_std[0, 0]), 4.0, abs_tol=0.35)
        assert math.isclose(float(per_pixel_std[5, 10]), 4.0, abs_tol=0.35)
        assert math.isclose(float(per_pixel_std[19, 19]), 6.0, abs_tol=0.45)
        assert math.isclose(float(per_pixel_std[15, 10]), 6.0, abs_tol=0.45)

    def test_sample_shadow_fading_validation(self):
        los_mask = np.ones((10, 10), dtype=bool)
        with pytest.raises(ValueError, match="resolution_m"):
            sample_shadow_fading_map(CellType.MACRO, los_mask, resolution_m=0.0)
        with pytest.raises(ValueError, match="resolution_m"):
            sample_shadow_fading_map(CellType.MACRO, los_mask, resolution_m=-5.0)
        with pytest.raises(ValueError, match="2D"):
            sample_shadow_fading_map(CellType.MACRO, np.ones((10,), dtype=bool), resolution_m=5.0)

    def test_compute_propagation_matrix_shadow_fading_integration(self):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.DENSE_URBAN)
        geom = grid.geometry_from_tx(Point3D(50.0, 50.0, 25.0))

        # Default: include_shadow_fading=False
        prop_no_sf = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=3.5,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            seed=42,
            include_shadow_fading=False,
        )
        assert hasattr(prop_no_sf, "shadow_fading_db")
        assert np.all(prop_no_sf.shadow_fading_db == 0.0)

        # Active: include_shadow_fading=True
        prop_with_sf = compute_propagation_matrix(
            CellType.MACRO,
            freq_ghz=3.5,
            h_bs_m=25.0,
            h_ut_m=1.5,
            grid_geom=geom,
            seed=42,
            include_shadow_fading=True,
            resolution_m=5.0,
        )
        assert np.any(prop_with_sf.shadow_fading_db != 0.0)
        # loss_db must be base_loss + shadow_fading_db
        np.testing.assert_allclose(
            prop_with_sf.loss_db,
            prop_no_sf.loss_db + prop_with_sf.shadow_fading_db,
            rtol=1e-5,
            atol=1e-5,
        )
