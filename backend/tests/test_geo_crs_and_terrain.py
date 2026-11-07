"""Tests for geospatial adapter ran_city.geo (CRS transformation and terrain sampling)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import rasterio
from hypothesis import given
from hypothesis import strategies as st
from rasterio.transform import from_origin

from ran_city.domain.grid import EnvironmentType, ScenarioGrid
from ran_city.geo.crs import utm30_to_wgs84, wgs84_to_utm30
from ran_city.geo.terrain import sample_grid_terrain, sample_points_elevation


class TestGeoCrs:
    """Tests for WGS84 (EPSG:4326) <-> ETRS89 / UTM zone 30N (EPSG:25830)."""

    def test_jaen_coordinates_and_scalar_roundtrip(self):
        # Jaén center / Castillo de Santa Catalina & Cathedral approx lon/lat
        lon_jaen = -3.7903
        lat_jaen = 37.7692

        x_m, y_m = wgs84_to_utm30(lon_jaen, lat_jaen)

        # Expected UTM30N coordinates in Jaén: x in [429_000, 432_000], y in [4_179_000, 4_182_000]
        assert 429_000.0 <= x_m <= 432_000.0, f"x_m={x_m} out of expected Jaen range"
        assert 4_179_000.0 <= y_m <= 4_182_000.0, f"y_m={y_m} out of expected Jaen range"

        # Roundtrip scalar check (< 1e-7 deg and < 1 mm metric error per CA-5)
        lon_back, lat_back = utm30_to_wgs84(x_m, y_m)
        assert math.isclose(lon_back, lon_jaen, abs_tol=1e-7)
        assert math.isclose(lat_back, lat_jaen, abs_tol=1e-7)
        x_back, y_back = wgs84_to_utm30(lon_back, lat_back)
        assert math.hypot(x_back - x_m, y_back - y_m) < 1e-3

    def test_array_roundtrip(self):
        lons = np.array([-3.82, -3.7903, -3.76], dtype=np.float64)
        lats = np.array([37.76, 37.7692, 37.80], dtype=np.float64)

        xs, ys = wgs84_to_utm30(lons, lats)
        assert isinstance(xs, np.ndarray)
        assert isinstance(ys, np.ndarray)
        assert xs.shape == lons.shape
        assert ys.shape == lats.shape

        lons_back, lats_back = utm30_to_wgs84(xs, ys)
        np.testing.assert_allclose(lons_back, lons, atol=1e-7)
        np.testing.assert_allclose(lats_back, lats, atol=1e-7)

    @given(
        lon=st.floats(min_value=-6.0, max_value=0.0),
        lat=st.floats(min_value=36.0, max_value=43.5),
    )
    def test_utm30_roundtrip_hypothesis(self, lon: float, lat: float):
        # Roundtrip within Zone 30N in mainland Spain
        x_m, y_m = wgs84_to_utm30(lon, lat)
        lon_back, lat_back = utm30_to_wgs84(x_m, y_m)

        assert math.isclose(lon_back, lon, abs_tol=1e-7)
        assert math.isclose(lat_back, lat, abs_tol=1e-7)

        # Monotonicity checks: small increment in lon increases x_m
        d_lon = 0.01
        x_m_east, _ = wgs84_to_utm30(lon + d_lon, lat)
        assert x_m_east > x_m

        # Small increment in lat increases y_m
        d_lat = 0.01
        _, y_m_north = wgs84_to_utm30(lon, lat + d_lat)
        assert y_m_north > y_m


@pytest.fixture
def synthetic_jaen_dem_geotiff(tmp_path: Path) -> Path:
    """Create a synthetic GeoTIFF in EPSG:25830 representing a topographic ramp in Jaén.

    Covers x: [428_000, 434_000], y: [4_178_000, 4_184_000] (6 km x 6 km).
    Resolution: 50 m per pixel -> 120 x 120 pixels.
    Elevation: from 430.0 m (north) to 815.0 m (south, e.g. Santa Catalina).
    """
    dem_file = tmp_path / "jaen_synthetic_mdt.tif"

    width = 120
    height = 120
    pixel_size = 50.0

    # Top-left corner: x_min = 428000, y_max = 4184000
    transform = from_origin(428_000.0, 4_184_000.0, pixel_size, pixel_size)

    # Ramp: row 0 (north) has ~430m, row 119 (south) has ~815m
    row_fractions = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    elevation_data = 430.0 + (815.0 - 430.0) * row_fractions
    elevation_data = np.tile(elevation_data, (1, width))

    with rasterio.open(
        dem_file,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=np.float32,
        crs="EPSG:25830",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(elevation_data, 1)

    return dem_file


class TestGeoTerrain:
    """Tests for sampling elevations from EPSG:25830 rasters onto points and ScenarioGrid."""

    def test_sample_points_elevation_exact(self, synthetic_jaen_dem_geotiff: Path):
        # Sample top-left (north), center, and bottom-right (south)
        xs = [428_025.0, 431_000.0, 433_975.0]
        ys = [4_183_975.0, 4_181_000.0, 4_178_025.0]

        elevations = sample_points_elevation(synthetic_jaen_dem_geotiff, xs, ys)
        assert isinstance(elevations, np.ndarray)
        assert elevations.shape == (3,)
        assert np.all(np.isfinite(elevations))

        # North should be ~430 m, South should be ~815 m
        assert math.isclose(elevations[0], 430.0, abs_tol=1.0)
        assert math.isclose(elevations[2], 815.0, abs_tol=1.0)
        assert elevations[0] < elevations[1] < elevations[2]

    def test_sample_grid_terrain_shape_and_no_nans(self, synthetic_jaen_dem_geotiff: Path):
        # Grid inside DEM bounds
        grid = ScenarioGrid.from_bounds(
            x_min=429_000.0,
            y_min=4_179_000.0,
            x_max=433_000.0,
            y_max=4_183_000.0,
            environment=EnvironmentType.RURAL,  # 50m resolution
        )

        grid_with_dem = sample_grid_terrain(synthetic_jaen_dem_geotiff, grid)

        assert grid_with_dem.terrain_z_m is not None
        assert grid_with_dem.terrain_z_m.shape == grid.shape
        assert not np.isnan(grid_with_dem.terrain_z_m).any()
        assert not np.isinf(grid_with_dem.terrain_z_m).any()

        # Check values are within the ramp bounds
        assert np.all(grid_with_dem.terrain_z_m >= 430.0 - 1e-3)
        assert np.all(grid_with_dem.terrain_z_m <= 815.0 + 1e-3)

    def test_sample_out_of_bounds_safe_fallback(self, synthetic_jaen_dem_geotiff: Path):
        # Sample points clearly outside raster bounds
        xs = [100_000.0, 900_000.0]
        ys = [1_000_000.0, 9_000_000.0]

        elevations = sample_points_elevation(synthetic_jaen_dem_geotiff, xs, ys)
        assert isinstance(elevations, np.ndarray)
        assert elevations.shape == (2,)
        # Must not produce NaNs or infs; replaces with valid fallback (e.g. median/edge)
        assert np.all(np.isfinite(elevations))
        assert not np.isnan(elevations).any()
