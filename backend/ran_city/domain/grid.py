"""Spatial grid and geometry calculations for RF simulation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from ran_city.domain.units import Point3D


class EnvironmentType(str, Enum):
    """Categorization of geographical environment and associated grid resolution."""

    DENSE_URBAN = "dense_urban"
    URBAN = "urban"
    RURAL = "rural"

    @property
    def resolution_m(self) -> float:
        """Grid resolution in meters according to course notes (001_propagacion_mallado_T2)."""
        match self:
            case EnvironmentType.DENSE_URBAN:
                return 5.0
            case EnvironmentType.URBAN:
                return 12.0
            case EnvironmentType.RURAL:
                return 50.0


@dataclass(frozen=True, slots=True)
class GridGeometry:
    """Precomputed 2D geometric tensors from a transmitter (TX) to every grid pixel (RX).

    All matrices share the same 2D shape (n_y, n_x).
    """

    d2d_m: np.ndarray
    d3d_m: np.ndarray
    zenith_gcs_deg: np.ndarray
    azimuth_gcs_deg: np.ndarray


@dataclass(frozen=True, slots=True)
class ScenarioGrid:
    """Regular 2D simulation grid in metric CRS (EPSG:25830).

    Matrices are arranged with shape (n_y, n_x) indexed as [y_idx, x_idx].
    """

    x_min: float
    y_min: float
    x_max: float
    y_max: float
    environment: EnvironmentType
    ground_z_m: float
    rx_height_m: float
    xs: np.ndarray
    ys: np.ndarray
    xx_m: np.ndarray
    yy_m: np.ndarray

    @classmethod
    def from_bounds(
        cls,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
        environment: EnvironmentType,
        ground_z_m: float = 0.0,
        rx_height_m: float = 1.5,
    ) -> ScenarioGrid:
        """Create a ScenarioGrid covering the bounding box with regular cell centers."""
        if x_max <= x_min:
            raise ValueError(f"x_max ({x_max}) must be strictly greater than x_min ({x_min})")
        if y_max <= y_min:
            raise ValueError(f"y_max ({y_max}) must be strictly greater than y_min ({y_min})")
        if rx_height_m < 0.0:
            raise ValueError(f"rx_height_m must be non-negative, got {rx_height_m}")

        res = environment.resolution_m
        if (x_max - x_min) < res:
            raise ValueError(
                f"Bounding box width ({x_max - x_min} m) is smaller than resolution ({res} m)"
            )
        if (y_max - y_min) < res:
            raise ValueError(
                f"Bounding box height ({y_max - y_min} m) is smaller than resolution ({res} m)"
            )

        xs = np.arange(x_min + res / 2.0, x_max, res)
        ys = np.arange(y_min + res / 2.0, y_max, res)
        xx_m, yy_m = np.meshgrid(xs, ys, indexing="xy")

        return cls(
            x_min=float(x_min),
            y_min=float(y_min),
            x_max=float(x_max),
            y_max=float(y_max),
            environment=environment,
            ground_z_m=float(ground_z_m),
            rx_height_m=float(rx_height_m),
            xs=xs,
            ys=ys,
            xx_m=xx_m,
            yy_m=yy_m,
        )

    @property
    def shape(self) -> tuple[int, int]:
        """Grid dimensions as (n_y, n_x)."""
        return self.xx_m.shape

    def geometry_from_tx(self, tx_pos: Point3D, min_d3d_m: float = 1.0) -> GridGeometry:
        """Compute 2D/3D distances and spherical angles (GCS) from transmitter to each cell center.

        Conventions:
        - Vector points from TX to RX:
          dx = x_rx - x_tx, dy = y_rx - y_tx, dz = z_rx - z_tx.
        - Azimuth follows compass convention:
          0° = North (+y), 90° = East (+x), 180° = South (-y), 270° = West (-x).
          azimuth = arctan2(dx, dy) % 360.0
        - Zenith follows 3GPP TR 38.901 Clause 7.1:
          0° = zenith, 90° = horizon, 180° = nadir.
          zenith = arccos(dz / d3d). If TX is higher than RX (dz < 0), zenith > 90° (downtilt).
        """
        dx = self.xx_m - tx_pos.x_m
        dy = self.yy_m - tx_pos.y_m
        dz = (self.ground_z_m + self.rx_height_m) - tx_pos.z_m

        d2d_m = np.hypot(dx, dy)
        raw_d3d = np.sqrt(d2d_m**2 + dz**2)

        safe_raw_d3d = np.where(raw_d3d > 0.0, raw_d3d, 1.0)
        cos_zenith = np.clip(dz / safe_raw_d3d, -1.0, 1.0)
        zenith_gcs_deg = np.where(raw_d3d == 0.0, 90.0, np.degrees(np.arccos(cos_zenith)))

        d3d_m = np.maximum(min_d3d_m, raw_d3d)
        azimuth_gcs_deg = np.degrees(np.arctan2(dx, dy)) % 360.0

        return GridGeometry(
            d2d_m=d2d_m,
            d3d_m=d3d_m,
            zenith_gcs_deg=zenith_gcs_deg,
            azimuth_gcs_deg=azimuth_gcs_deg,
        )
