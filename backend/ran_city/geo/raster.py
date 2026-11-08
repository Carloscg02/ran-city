"""Raster WebGL export and PNG RGBA encoding for Deck.gl / MapLibre visualization."""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image

from ran_city.domain.grid import ScenarioGrid
from ran_city.geo.crs import utm30_to_wgs84


@dataclass(frozen=True, slots=True)
class RasterOverlay:
    """Exported raster PNG with geographic bounds for deck.gl BitmapLayer."""

    png_bytes: bytes
    bounds_wgs84: tuple[float, float, float, float]  # (west, south, east, north)
    width: int
    height: int


# Qualitative categorical palette (12 visually distinct colors for best server cell indices)
CATEGORICAL_PALETTE: tuple[tuple[int, int, int], ...] = (
    (31, 119, 180),    # Blue
    (255, 127, 14),   # Orange
    (44, 160, 44),    # Green
    (214, 39, 40),    # Red
    (148, 103, 189),  # Purple
    (140, 86, 75),    # Brown
    (227, 119, 194),  # Pink
    (127, 127, 127),  # Gray
    (188, 189, 34),   # Yellow-green
    (23, 190, 207),   # Cyan
    (255, 187, 120),  # Light orange
    (152, 223, 138),  # Light green
)

# Continuous scientific color ramp stops: [pos, R, G, B]
# Deep Blue -> Cyan -> Green -> Amber -> Red/Crimson
RAMP_STOPS: tuple[tuple[float, int, int, int], ...] = (
    (0.00, 13, 8, 135),
    (0.25, 53, 132, 236),
    (0.50, 70, 193, 150),
    (0.75, 246, 175, 40),
    (1.00, 220, 40, 40),
)


def compute_grid_wgs84_bounds(grid: ScenarioGrid) -> tuple[float, float, float, float]:
    """Calculate the WGS84 bounding box (west, south, east, north) of a ScenarioGrid.

    Projects the four metric corners of the grid from EPSG:25830 to EPSG:4326.

    Args:
        grid: Metric simulation grid in EPSG:25830.

    Returns:
        Tuple of (west, south, east, north) in EPSG:4326.
    """
    x_corners = np.array([grid.x_min, grid.x_max, grid.x_max, grid.x_min], dtype=np.float64)
    y_corners = np.array([grid.y_min, grid.y_min, grid.y_max, grid.y_max], dtype=np.float64)

    lons, lats = utm30_to_wgs84(x_corners, y_corners)
    west = float(np.min(lons))
    south = float(np.min(lats))
    east = float(np.max(lons))
    north = float(np.max(lats))

    return (west, south, east, north)


def encode_matrix_png_rgba(
    matrix: np.ndarray,
    vmin: float = -125.0,
    vmax: float = -65.0,
    alpha: int = 200,
    min_threshold: float | None = None,
    categorical: bool = False,
) -> bytes:
    """Encode a 2D scalar matrix to a PNG RGBA byte string for deck.gl BitmapLayer.

    Applies np.flipud so row 0 in the generated PNG matches the Northern edge (y_max)
    in deck.gl / WebGL texture space.

    Args:
        matrix: 2D NumPy array with shape (n_y, n_x).
        vmin: Minimum value for continuous colormap normalization.
        vmax: Maximum value for continuous colormap normalization.
        alpha: Alpha channel opacity [0..255] for valid non-transparent pixels.
        min_threshold: Optional threshold below which pixels are made transparent (alpha=0).
        categorical: If True, treats values as integer category indices using a distinct palette.

    Returns:
        Raw bytes of the RGBA PNG image.
    """
    mat = np.asarray(matrix, dtype=np.float64)
    if mat.ndim != 2:
        raise ValueError(f"Expected 2D matrix, got ndim={mat.ndim}")

    # Flip vertically: deck.gl row 0 is North (y_max), whereas grid row 0 is South (y_min)
    flipped = np.flipud(mat)
    n_y, n_x = flipped.shape

    rgba = np.zeros((n_y, n_x, 4), dtype=np.uint8)

    valid_mask = np.isfinite(flipped)
    if min_threshold is not None:
        valid_mask = valid_mask & (flipped >= min_threshold)

    if categorical:
        # Categorical palette mapping
        palette_arr = np.array(CATEGORICAL_PALETTE, dtype=np.uint8)
        num_colors = len(palette_arr)

        # Non-negative integer indices
        cat_indices = np.where(valid_mask, np.round(flipped).astype(np.int64), 0)
        color_indices = cat_indices % num_colors
        rgb = palette_arr[color_indices]

        rgba[..., :3] = rgb
        rgba[..., 3] = np.where(valid_mask, np.uint8(alpha), np.uint8(0))
    else:
        # Continuous normalized colormap
        if vmax <= vmin:
            raise ValueError(f"vmax ({vmax}) must be strictly greater than vmin ({vmin})")

        norm = np.nan_to_num((flipped - vmin) / (vmax - vmin), nan=0.0, posinf=1.0, neginf=0.0)
        norm = np.clip(norm, 0.0, 1.0)
        norm_flat = norm.ravel()

        stop_positions = [s[0] for s in RAMP_STOPS]
        stop_r = [s[1] for s in RAMP_STOPS]
        stop_g = [s[2] for s in RAMP_STOPS]
        stop_b = [s[3] for s in RAMP_STOPS]

        r = np.interp(norm_flat, stop_positions, stop_r).reshape((n_y, n_x))
        g = np.interp(norm_flat, stop_positions, stop_g).reshape((n_y, n_x))
        b = np.interp(norm_flat, stop_positions, stop_b).reshape((n_y, n_x))

        rgba[..., 0] = np.round(r).astype(np.uint8)
        rgba[..., 1] = np.round(g).astype(np.uint8)
        rgba[..., 2] = np.round(b).astype(np.uint8)
        rgba[..., 3] = np.where(valid_mask, np.uint8(alpha), np.uint8(0))

    img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
