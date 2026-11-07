"""3GPP TR 38.901 antenna models and coordinate transformations.

Implements the single element radiation pattern (Clause 7.3, Table 7.3-1),
coordinate transformation from GCS to LCS with mechanical tilt (Clause 7.1.3),
and Uniform Planar Array (UPA) factor with electrical tilt and scan (ITU-R M.2101-0 Sec. 5).
"""

from __future__ import annotations

import numpy as np

from ran_city.domain.grid import GridGeometry
from ran_city.domain.models import AntennaConfig


def gcs_to_lcs_angles(
    zenith_gcs_deg: float | np.ndarray,
    azimuth_gcs_deg: float | np.ndarray,
    sector_azimuth_deg: float,
    mechanical_tilt_deg: float = 0.0,
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Convert global spherical angles (GCS) to local coordinate system (LCS) angles.

    Follows 3GPP TR 38.901 Clause 7.1.3 (Eq. 7.1-7 and 7.1-8) with zero slant (gamma = 0).

    Args:
        zenith_gcs_deg: Zenith angle in GCS in degrees (0°=zenith, 90°=horizon, 180°=nadir).
        azimuth_gcs_deg: Azimuth angle in GCS in degrees (compass convention, 0°=North, clockwise).
        sector_azimuth_deg: Sector bearing / bearing of antenna normal in GCS (0°=North, clockwise).
        mechanical_tilt_deg: Mechanical downtilt in degrees (>0 tilts antenna downwards toward ground).

    Returns:
        Tuple (zenith_lcs_deg, azimuth_lcs_deg) in local antenna coordinates.
    """
    is_scalar = np.isscalar(zenith_gcs_deg) and np.isscalar(azimuth_gcs_deg)

    # Relative azimuth difference wrapped to [-180.0, 180.0)
    delta_az_deg = (
        (np.asarray(azimuth_gcs_deg, dtype=float) - float(sector_azimuth_deg) + 180.0) % 360.0
    ) - 180.0

    theta = np.radians(np.asarray(zenith_gcs_deg, dtype=float))
    phi = np.radians(delta_az_deg)
    beta = np.radians(float(mechanical_tilt_deg))

    cos_theta_p = np.clip(
        np.cos(beta) * np.cos(theta) + np.sin(beta) * np.sin(theta) * np.cos(phi),
        -1.0,
        1.0,
    )
    zenith_lcs_deg = np.degrees(np.arccos(cos_theta_p))

    x_p = np.cos(beta) * np.sin(theta) * np.cos(phi) - np.sin(beta) * np.cos(theta)
    y_p = np.sin(theta) * np.sin(phi)
    azimuth_lcs_deg = np.degrees(np.arctan2(y_p, x_p))

    if is_scalar:
        return float(zenith_lcs_deg), float(azimuth_lcs_deg)
    return zenith_lcs_deg, azimuth_lcs_deg


def element_gain_dbi(
    zenith_lcs_deg: float | np.ndarray,
    azimuth_lcs_deg: float | np.ndarray,
    g_max_dbi: float = 8.0,
    theta_3db_deg: float = 65.0,
    phi_3db_deg: float = 65.0,
    sla_v_db: float = 30.0,
    a_max_db: float = 30.0,
) -> float | np.ndarray:
    """Radiation power pattern of a single antenna element in dBi.

    Follows 3GPP TR 38.901 Clause 7.3, Table 7.3-1.

    Args:
        zenith_lcs_deg: Zenith angle in local coordinates (90° = boresight / horizon).
        azimuth_lcs_deg: Azimuth angle in local coordinates (0° = boresight).
        g_max_dbi: Maximum directional gain of a single element (default: 8.0 dBi).
        theta_3db_deg: Vertical 3dB half-power beamwidth (default: 65.0°).
        phi_3db_deg: Horizontal 3dB half-power beamwidth (default: 65.0°).
        sla_v_db: Sidelobe attenuation limit in vertical plane (default: 30.0 dB).
        a_max_db: Front-to-back attenuation limit (default: 30.0 dB).

    Returns:
        Gain in dBi as a float (if inputs are scalars) or np.ndarray.
    """
    is_scalar = np.isscalar(zenith_lcs_deg) and np.isscalar(azimuth_lcs_deg)

    phi_deg = ((np.asarray(azimuth_lcs_deg, dtype=float) + 180.0) % 360.0) - 180.0
    theta_deg = np.asarray(zenith_lcs_deg, dtype=float)

    a_ev = -np.minimum(12.0 * ((theta_deg - 90.0) / theta_3db_deg) ** 2, sla_v_db)
    a_eh = -np.minimum(12.0 * (phi_deg / phi_3db_deg) ** 2, a_max_db)
    gain = g_max_dbi - np.minimum(-(a_ev + a_eh), a_max_db)

    if is_scalar:
        return float(gain)
    return gain


def _dirichlet_factor(delta_psi: np.ndarray, n: int) -> np.ndarray:
    """Evaluate closed-form Dirichlet power factor |sin(N * psi / 2) / sin(psi / 2)|^2."""
    if n == 1:
        return np.ones_like(delta_psi, dtype=float)
    half_psi = 0.5 * delta_psi
    denom = np.sin(half_psi)
    near_zero = np.abs(denom) < 1e-12
    safe_denom = np.where(near_zero, 1.0, denom)
    ratio = np.sin(n * half_psi) / safe_denom
    return np.where(near_zero, float(n**2), ratio**2)


def panel_gain_dbi(
    zenith_lcs_deg: float | np.ndarray,
    azimuth_lcs_deg: float | np.ndarray,
    antenna: AntennaConfig,
    min_af_linear: float = 1e-4,
) -> float | np.ndarray:
    """Compute directional gain in dBi of a Uniform Planar Array (UPA) of antenna elements.

    Follows 3GPP TR 38.901 Clause 7.3 and ITU-R M.2101-0 Section 5.
    Normalizes weights to |w_{m,n}| = 1 / sqrt(N_V * N_H) and applies electrical tilt and scan.

    Args:
        zenith_lcs_deg: Zenith angle in local coordinates.
        azimuth_lcs_deg: Azimuth angle in local coordinates.
        antenna: Antenna configuration (element spacing, rows, cols, electrical tilt/scan).
        min_af_linear: Floor for array factor to avoid -inf in nulls (default: 1e-4 = -40 dB).

    Returns:
        Array gain in dBi as float or np.ndarray.
    """
    is_scalar = np.isscalar(zenith_lcs_deg) and np.isscalar(azimuth_lcs_deg)

    theta_p = np.radians(np.asarray(zenith_lcs_deg, dtype=float))
    phi_p = np.radians(np.asarray(azimuth_lcs_deg, dtype=float))
    theta_steer = np.radians(90.0 + antenna.electrical_tilt_deg)
    phi_steer = np.radians(antenna.electrical_scan_deg)

    delta_psi_v = 2.0 * np.pi * antenna.d_v_wavelengths * (np.cos(theta_p) - np.cos(theta_steer))
    delta_psi_h = (
        2.0
        * np.pi
        * antenna.d_h_wavelengths
        * (np.sin(theta_p) * np.sin(phi_p) - np.sin(theta_steer) * np.sin(phi_steer))
    )

    factor_v = _dirichlet_factor(delta_psi_v, antenna.n_rows)
    factor_h = _dirichlet_factor(delta_psi_h, antenna.n_cols)

    af_linear = (factor_v * factor_h) / float(antenna.n_rows * antenna.n_cols)
    af_db = 10.0 * np.log10(np.maximum(af_linear, min_af_linear))

    e_gain = element_gain_dbi(zenith_lcs_deg, azimuth_lcs_deg, g_max_dbi=antenna.g_element_max_dbi)
    total_gain = e_gain + af_db

    if is_scalar:
        return float(total_gain)
    return total_gain


def compute_antenna_gain_matrix(
    antenna: AntennaConfig,
    sector_azimuth_deg: float,
    grid_geom: GridGeometry,
) -> np.ndarray:
    """Compute 2D matrix of antenna gain in dBi over a ScenarioGrid geometry.

    Args:
        antenna: Antenna configuration with tilt and array specifications.
        sector_azimuth_deg: Azimuth pointing direction of sector in GCS degrees.
        grid_geom: GridGeometry precomputed from transmitter to grid pixels.

    Returns:
        2D array of antenna gain in dBi with shape matching grid_geom.d2d_m.
    """
    zenith_lcs, azimuth_lcs = gcs_to_lcs_angles(
        grid_geom.zenith_gcs_deg,
        grid_geom.azimuth_gcs_deg,
        sector_azimuth_deg=sector_azimuth_deg,
        mechanical_tilt_deg=antenna.mechanical_tilt_deg,
    )
    gain_mat = panel_gain_dbi(zenith_lcs, azimuth_lcs, antenna)
    return np.asarray(gain_mat, dtype=float)
