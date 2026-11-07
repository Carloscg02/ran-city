"""CRS transformation utilities between WGS84 (EPSG:4326) and ETRS89 / UTM zone 30N (EPSG:25830)."""

from __future__ import annotations

import numpy as np
import pyproj

# Module-level cached transformers
# always_xy=True forces (lon, lat) ordering for EPSG:4326 and (x, y) for EPSG:25830
_WGS84_TO_UTM30 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
_UTM30_TO_WGS84 = pyproj.Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)


def wgs84_to_utm30(
    lon: float | np.ndarray,
    lat: float | np.ndarray,
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Transform geographic coordinates (WGS84, lon/lat) to UTM zone 30N (ETRS89, x/y meters).

    Args:
        lon: Longitude in degrees (scalar or array).
        lat: Latitude in degrees (scalar or array).

    Returns:
        Tuple of (x_m, y_m) in EPSG:25830.
    """
    is_array = isinstance(lon, np.ndarray) or isinstance(lat, np.ndarray)
    x, y = _WGS84_TO_UTM30.transform(lon, lat)
    if is_array:
        return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    return float(x), float(y)


def utm30_to_wgs84(
    x_m: float | np.ndarray,
    y_m: float | np.ndarray,
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Transform UTM zone 30N (ETRS89, x/y meters) to geographic coordinates (WGS84, lon/lat).

    Args:
        x_m: Easting in meters (scalar or array).
        y_m: Northing in meters (scalar or array).

    Returns:
        Tuple of (lon, lat) in EPSG:4326.
    """
    is_array = isinstance(x_m, np.ndarray) or isinstance(y_m, np.ndarray)
    lon, lat = _UTM30_TO_WGS84.transform(x_m, y_m)
    if is_array:
        return np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64)
    return float(lon), float(lat)
