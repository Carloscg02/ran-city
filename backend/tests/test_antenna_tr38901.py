"""Tests for 3GPP TR 38.901 antenna models (element, mechanical tilt, and UPA array)."""

import math

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from ran_city.antenna.tr38901 import (
    compute_antenna_gain_matrix,
    element_gain_dbi,
    gcs_to_lcs_angles,
    panel_gain_dbi,
)
from ran_city.domain.grid import EnvironmentType, ScenarioGrid
from ran_city.domain.models import AntennaConfig
from ran_city.domain.units import Point3D


class TestElementGainTR38901:
    """Tests for single element radiation pattern (3GPP TR 38.901 Table 7.3-1)."""

    def test_element_gain_table_731_exact_values(self):
        # Boresight: (90°, 0°) -> 8.0 dBi
        assert math.isclose(element_gain_dbi(90.0, 0.0), 8.0, abs_tol=1e-5)

        # 3 dB beamwidth points (theta_3dB = 65°, phi_3dB = 65°): 8.0 - 3.0 = 5.0 dBi
        assert math.isclose(element_gain_dbi(90.0 + 32.5, 0.0), 5.0, abs_tol=1e-5)
        assert math.isclose(element_gain_dbi(90.0 - 32.5, 0.0), 5.0, abs_tol=1e-5)
        assert math.isclose(element_gain_dbi(90.0, 32.5), 5.0, abs_tol=1e-5)
        assert math.isclose(element_gain_dbi(90.0, -32.5), 5.0, abs_tol=1e-5)

        # Back lobe: phi = 180° -> A_max = 30 dB -> 8.0 - 30.0 = -22.0 dBi
        assert math.isclose(element_gain_dbi(90.0, 180.0), -22.0, abs_tol=1e-5)
        assert math.isclose(element_gain_dbi(90.0, -180.0), -22.0, abs_tol=1e-5)

        # Vertical cut at zenith (0°) and nadir (180°) for phi=0°:
        # A_ev = 12 * (90/65)^2 = 23.005917 dB -> 8.0 - 23.005917 = -15.005917 dBi
        expected_zenith_phi0 = 8.0 - 12.0 * (90.0 / 65.0) ** 2
        assert math.isclose(element_gain_dbi(0.0, 0.0), expected_zenith_phi0, abs_tol=1e-5)
        assert math.isclose(element_gain_dbi(180.0, 0.0), expected_zenith_phi0, abs_tol=1e-5)

        # Poles combined with side/back attenuation saturate at A_max = 30 dB -> -22.0 dBi
        assert math.isclose(element_gain_dbi(0.0, 90.0), -22.0, abs_tol=1e-5)
        assert math.isclose(element_gain_dbi(180.0, 90.0), -22.0, abs_tol=1e-5)
        assert math.isclose(element_gain_dbi(0.0, 180.0), -22.0, abs_tol=1e-5)


class TestGcsToLcsAngles:
    """Tests for GCS to LCS rotation under mechanical tilt (TR 38.901 Clause 7.1.3)."""

    def test_boresight_with_mechanical_tilt(self):
        # Sector facing North (az=0°), mechanical tilt beta = 10° (downtilt)
        # In front at horizon (theta_gcs=90°, az_gcs=0°):
        # In LCS, wave is coming from 10° above LCS horizon -> theta_lcs = 80°
        theta_lcs, phi_lcs = gcs_to_lcs_angles(
            90.0, 0.0, sector_azimuth_deg=0.0, mechanical_tilt_deg=10.0
        )
        assert math.isclose(theta_lcs, 80.0, abs_tol=1e-5)
        assert math.isclose(phi_lcs, 0.0, abs_tol=1e-5)

        # Pointing directly at main beam (theta_gcs=100°, az_gcs=0°):
        # Downtilt beta=10° aligns with theta_gcs=100°, so in LCS theta_lcs = 90° (boresight)
        theta_lcs, phi_lcs = gcs_to_lcs_angles(
            100.0, 0.0, sector_azimuth_deg=0.0, mechanical_tilt_deg=10.0
        )
        assert math.isclose(theta_lcs, 90.0, abs_tol=1e-5)
        assert math.isclose(phi_lcs, 0.0, abs_tol=1e-5)

    def test_mechanical_tilt_lateral_and_back(self):
        sector_az = 45.0
        beta = 10.0

        # Laterals (az_gcs = sector_az ± 90°, theta_gcs = 90°):
        # cos(theta') = cos(10°)*cos(90°) + sin(10°)*sin(90°)*cos(±90°) = 0 -> theta_lcs = 90°
        for delta in (-90.0, 90.0):
            theta_lcs, phi_lcs = gcs_to_lcs_angles(90.0, sector_az + delta, sector_az, beta)
            assert math.isclose(theta_lcs, 90.0, abs_tol=1e-5)
            assert math.isclose(abs(phi_lcs), 90.0, abs_tol=1e-5)

        # Back (az_gcs = sector_az + 180°, theta_gcs = 80°):
        # Uplifted back lobe reaches LCS horizon (theta_lcs = 90°)
        theta_lcs, phi_lcs = gcs_to_lcs_angles(80.0, sector_az + 180.0, sector_az, beta)
        assert math.isclose(theta_lcs, 90.0, abs_tol=1e-5)
        assert math.isclose(abs(phi_lcs), 180.0, abs_tol=1e-5)


class TestPanelGainTR38901:
    """Tests for UPA panel gain and mechanical vs electrical tilt contrast."""

    def test_1x1_panel_matches_single_element(self):
        ant_1x1 = AntennaConfig(n_rows=1, n_cols=1, g_element_max_dbi=8.0)
        test_angles = [(90.0, 0.0), (100.0, 15.0), (75.0, -30.0), (90.0, 180.0)]
        for th, ph in test_angles:
            p_gain = panel_gain_dbi(th, ph, ant_1x1)
            e_gain = element_gain_dbi(th, ph, g_max_dbi=8.0)
            assert math.isclose(p_gain, e_gain, abs_tol=1e-6)

    def test_8x8_boresight_peak_gain(self):
        ant_8x8 = AntennaConfig(n_rows=8, n_cols=8, g_element_max_dbi=8.0)
        # Peak gain = 8.0 + 10 * log10(64) = 8.0 + 18.0617997 = 26.0618 dBi
        expected_peak = 8.0 + 10.0 * math.log10(64.0)
        gain = panel_gain_dbi(90.0, 0.0, ant_8x8)
        assert math.isclose(gain, expected_peak, abs_tol=1e-4)
        assert math.isclose(gain, 26.0618, abs_tol=1e-3)

    def test_physical_contrast_mechanical_vs_electrical_tilt(self):
        # Target direction in GCS: theta_gcs = 100° (10° downtilt), az_gcs = 0°
        # Sector facing North (0°)
        theta_gcs = 100.0
        az_gcs = 0.0
        sector_az = 0.0

        # Case A: Mechanical tilt = 10°, Electrical tilt = 0°
        ant_mech = AntennaConfig(
            n_rows=8,
            n_cols=8,
            g_element_max_dbi=8.0,
            mechanical_tilt_deg=10.0,
            electrical_tilt_deg=0.0,
        )
        th_lcs_mech, ph_lcs_mech = gcs_to_lcs_angles(
            theta_gcs, az_gcs, sector_az, ant_mech.mechanical_tilt_deg
        )
        # LCS boresight reached: (90°, 0°)
        gain_mech = panel_gain_dbi(th_lcs_mech, ph_lcs_mech, ant_mech)
        # No scan loss: peak gain 26.0618 dBi
        assert math.isclose(gain_mech, 26.0618, abs_tol=1e-3)

        # Case B: Mechanical tilt = 0°, Electrical tilt = 10°
        ant_elec = AntennaConfig(
            n_rows=8,
            n_cols=8,
            g_element_max_dbi=8.0,
            mechanical_tilt_deg=0.0,
            electrical_tilt_deg=10.0,
        )
        th_lcs_elec, ph_lcs_elec = gcs_to_lcs_angles(
            theta_gcs, az_gcs, sector_az, ant_elec.mechanical_tilt_deg
        )
        assert math.isclose(th_lcs_elec, 100.0)
        assert math.isclose(ph_lcs_elec, 0.0)
        gain_elec = panel_gain_dbi(th_lcs_elec, ph_lcs_elec, ant_elec)
        # Array factor hits peak (+18.0618 dB), but element suffers scan loss:
        # scan_loss = 12 * (10 / 65)^2 = 0.28402 dB
        # gain = 26.0618 - 0.28402 = 25.7778 dBi
        expected_elec_gain = 26.0617997 - 12.0 * (10.0 / 65.0) ** 2
        assert math.isclose(gain_elec, expected_elec_gain, abs_tol=1e-4)
        assert math.isclose(gain_elec, 25.7778, abs_tol=1e-3)
        assert gain_mech > gain_elec  # Scan loss physically verified

    def test_compute_antenna_gain_matrix(self):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.DENSE_URBAN)
        tx = Point3D(50.0, 50.0, 25.0)
        geom = grid.geometry_from_tx(tx)

        ant = AntennaConfig(n_rows=8, n_cols=8, mechanical_tilt_deg=6.0, electrical_tilt_deg=2.0)
        gain_mat = compute_antenna_gain_matrix(ant, sector_azimuth_deg=90.0, grid_geom=geom)

        assert isinstance(gain_mat, np.ndarray)
        assert gain_mat.shape == grid.shape
        assert np.all(np.isfinite(gain_mat))  # No NaN, no inf even in array factor nulls
        # Must be bounded by theoretical maximum
        assert np.all(gain_mat <= 8.0 + 10.0 * math.log10(64.0) + 1e-6)

    @given(
        th_lcs=st.floats(min_value=1.0, max_value=179.0),
        ph_lcs=st.floats(min_value=-180.0, max_value=180.0),
        n_rows=st.integers(min_value=1, max_value=8),
        n_cols=st.integers(min_value=1, max_value=8),
    )
    def test_panel_gain_upper_bound_hypothesis(self, th_lcs, ph_lcs, n_rows, n_cols):
        ant = AntennaConfig(n_rows=n_rows, n_cols=n_cols, g_element_max_dbi=8.0)
        gain = panel_gain_dbi(th_lcs, ph_lcs, ant)
        max_theoretical = 8.0 + 10.0 * math.log10(float(n_rows * n_cols))
        assert gain <= max_theoretical + 1e-6

    @given(
        th_lcs=st.floats(min_value=1.0, max_value=179.0),
        ph_lcs=st.floats(min_value=0.0, max_value=180.0),
    )
    def test_azimuthal_symmetry_zero_scan_hypothesis(self, th_lcs, ph_lcs):
        ant = AntennaConfig(n_rows=4, n_cols=4, electrical_scan_deg=0.0)
        gain_pos = panel_gain_dbi(th_lcs, ph_lcs, ant)
        gain_neg = panel_gain_dbi(th_lcs, -ph_lcs, ant)
        assert math.isclose(gain_pos, gain_neg, rel_tol=1e-6, abs_tol=1e-6)
