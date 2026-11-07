"""Digital elevation model (DEM) sampling utilities for points and grids."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import rasterio

from ran_city.domain.grid import ScenarioGrid


def sample_points_elevation(
    raster_path: str | Path,
    xs_m: Sequence[float] | np.ndarray,
    ys_m: Sequence[float] | np.ndarray,
    fallback_elevation_m: float | None = None,
) -> np.ndarray:
    """Sample terrain elevation at given metric coordinates (EPSG:25830).

    Args:
        raster_path: Path to GeoTIFF elevation raster in EPSG:25830.
        xs_m: Easting coordinate(s) in meters.
        ys_m: Northing coordinate(s) in meters.
        fallback_elevation_m: Default elevation in meters if sample is invalid/out-of-bounds
            and raster median cannot be determined.

    Returns:
        1D numpy array of elevations in meters (float64) matching input coordinates shape/length.
    """
    path = Path(raster_path)
    if not path.is_file():
        raise FileNotFoundError(f"Terrain raster not found: {path}")

    arr_xs = np.asarray(xs_m, dtype=np.float64)
    arr_ys = np.asarray(ys_m, dtype=np.float64)

    if arr_xs.shape != arr_ys.shape:
        raise ValueError(f"Shape mismatch between xs_m {arr_xs.shape} and ys_m {arr_ys.shape}")

    orig_shape = arr_xs.shape
    flat_xs = arr_xs.ravel()
    flat_ys = arr_ys.ravel()

    coords = list(zip(flat_xs, flat_ys))
    if len(coords) == 0:
        return np.empty((0,), dtype=np.float64)

    with rasterio.open(path) as src:
        nodata = src.nodata
        left, bottom, right, top = src.bounds

        # Rasterio sample returns a generator of 1D arrays (one per band)
        raw_samples = np.array([sample[0] for sample in src.sample(coords)], dtype=np.float64)

        # Detect out of bounds or invalid / nodata
        oob_mask = (flat_xs < left) | (flat_xs > right) | (flat_ys < bottom) | (flat_ys > top)
        invalid_mask = oob_mask | np.isnan(raw_samples) | np.isinf(raw_samples)
        if nodata is not None:
            invalid_mask |= np.isclose(raw_samples, nodata)

        if np.any(invalid_mask):
            # Compute a safe fallback value: median of valid sampled values, or median of raster
            valid_samples = raw_samples[~invalid_mask]
            if len(valid_samples) > 0:
                safe_val = float(np.median(valid_samples))
            else:
                try:
                    band_data = src.read(1, masked=True)
                    if band_data.count() > 0:
                        safe_val = float(np.ma.median(band_data))
                    elif fallback_elevation_m is not None:
                        safe_val = float(fallback_elevation_m)
                    else:
                        safe_val = 0.0
                except (rasterio.errors.RasterioError, ValueError, RuntimeError):
                    safe_val = fallback_elevation_m if fallback_elevation_m is not None else 0.0

            raw_samples[invalid_mask] = safe_val

    return raw_samples.reshape(orig_shape)


def sample_grid_terrain(
    raster_path: str | Path,
    grid: ScenarioGrid,
    fallback_elevation_m: float | None = None,
) -> ScenarioGrid:
    """Sample terrain elevations from a GeoTIFF raster onto every pixel of a ScenarioGrid.

    Args:
        raster_path: Path to GeoTIFF raster in EPSG:25830.
        grid: ScenarioGrid to inject terrain onto.
        fallback_elevation_m: Optional fallback elevation for out-of-bounds/nodata cells.

    Returns:
        New ScenarioGrid with terrain_z_m populated.
    """
    elevations = sample_points_elevation(
        raster_path=raster_path,
        xs_m=grid.xx_m.ravel(),
        ys_m=grid.yy_m.ravel(),
        fallback_elevation_m=fallback_elevation_m,
    )
    terrain_z = elevations.reshape(grid.shape)
    return grid.with_terrain(terrain_z)
