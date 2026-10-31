"""RF and spatial domain units for RAN-city.

Provides explicit, immutable types for logarithmic powers (Dbm), relative gains/losses (Db),
linear powers (LinearMw), 3GPP angular conventions, and metric 3D points.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinearMw:
    """Linear power in milliwatts (mW). Must be non-negative."""

    value: float

    def __post_init__(self) -> None:
        if self.value < 0.0:
            raise ValueError(f"Linear power must be non-negative, got {self.value}")

    def to_dbm(self) -> Dbm:
        """Convert linear power (mW) to absolute logarithmic power (dBm)."""
        if self.value <= 0.0:
            raise ValueError("Linear power must be strictly positive to convert to dBm")
        return Dbm(10.0 * math.log10(self.value))

    def __add__(self, other: LinearMw) -> LinearMw:
        if not isinstance(other, LinearMw):
            return NotImplemented
        return LinearMw(self.value + other.value)

    def __mul__(self, factor: float) -> LinearMw:
        if not isinstance(factor, (int, float)):
            return NotImplemented
        return LinearMw(self.value * float(factor))

    def __rmul__(self, factor: float) -> LinearMw:
        return self.__mul__(factor)


@dataclass(frozen=True, slots=True)
class Db:
    """Relative gain or loss in decibels (dB)."""

    value: float

    def __add__(self, other: Db) -> Db:
        if not isinstance(other, Db):
            return NotImplemented
        return Db(self.value + other.value)

    def __sub__(self, other: Db) -> Db:
        if not isinstance(other, Db):
            return NotImplemented
        return Db(self.value - other.value)

    def __neg__(self) -> Db:
        return Db(-self.value)


@dataclass(frozen=True, slots=True)
class Dbm:
    """Absolute power in decibel-milliwatts (dBm)."""

    value: float

    def to_mw(self) -> LinearMw:
        """Convert logarithmic power (dBm) to linear power (mW)."""
        return LinearMw(10.0 ** (self.value / 10.0))

    def __add__(self, other: object) -> Dbm:
        if isinstance(other, Dbm):
            raise TypeError(
                "Absolute powers in dBm cannot be added directly. "
                "Convert to LinearMw to perform physical power addition."
            )
        if isinstance(other, Db):
            return Dbm(self.value + other.value)
        return NotImplemented

    def __sub__(self, other: object) -> Dbm | Db:
        if isinstance(other, Db):
            return Dbm(self.value - other.value)
        if isinstance(other, Dbm):
            return Db(self.value - other.value)
        return NotImplemented


@dataclass(frozen=True, slots=True)
class AzimuthDeg:
    """Azimuth angle in degrees following compass convention (0°=North, clockwise).

    Automatically normalized to [0.0, 360.0).
    """

    value: float

    def __init__(self, value: float) -> None:
        normalized = float(value) % 360.0
        # Guard against -0.0 in float modulo
        if normalized == 0.0:
            normalized = 0.0
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class ZenithDeg:
    """3GPP zenith angle in degrees (0°=zenith, 90°=horizon, 180°=nadir).

    Must satisfy 0.0 <= value <= 180.0.
    """

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 180.0):
            raise ValueError(f"Zenith angle must be in [0.0, 180.0] degrees, got {self.value}")


@dataclass(frozen=True, slots=True)
class Point3D:
    """Immutable 3D coordinate point in metric CRS (EPSG:25830)."""

    x_m: float
    y_m: float
    z_m: float
