"""Pydantic domain models for 5G NR network hierarchy and physical parameters."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ran_city.domain.units import Point3D


class DataSourceOrigin(str, Enum):
    """Traceability of network infrastructure origin."""

    REAL = "real"
    ESTIMATED = "estimated"
    SYNTHETIC = "synthetic"


class CellType(str, Enum):
    """Categorization of cell deployment type."""

    MACRO = "macro"
    MICRO = "micro"
    PICO = "pico"


class NrBand(BaseModel):
    """5G NR operating band parameters according to 3GPP TS 38.104 and TS 38.104-2."""

    model_config = ConfigDict(frozen=True)

    name: str
    n_band: int
    freq_ghz: float = Field(..., ge=0.5, le=100.0)
    scs_khz: int
    bandwidth_mhz: float = Field(..., gt=0.0)
    num_rbs: int = Field(..., ge=1)

    @field_validator("scs_khz")
    @classmethod
    def _validate_scs(cls, v: int) -> int:
        if v not in (15, 30, 60, 120):
            raise ValueError(f"scs_khz must be one of (15, 30, 60, 120), got {v}")
        return v

    @classmethod
    def n28(cls) -> NrBand:
        """Band n28 (700 MHz, FDD): 0.728 GHz DL, 15 kHz SCS, 20 MHz, 106 RBs (TS 38.104 Table 5.3.2-1)."""
        return cls(
            name="n28",
            n_band=28,
            freq_ghz=0.728,
            scs_khz=15,
            bandwidth_mhz=20.0,
            num_rbs=106,
        )

    @classmethod
    def n78(cls) -> NrBand:
        """Band n78 (3.5 GHz, TDD): 3.5 GHz, 30 kHz SCS, 100 MHz, 273 RBs (TS 38.104 Table 5.3.2-1)."""
        return cls(
            name="n78",
            n_band=78,
            freq_ghz=3.5,
            scs_khz=30,
            bandwidth_mhz=100.0,
            num_rbs=273,
        )

    @classmethod
    def n258(cls) -> NrBand:
        """Band n258 (26 GHz mmWave, TDD): 26.0 GHz, 120 kHz SCS, 100 MHz, 66 RBs (TS 38.104-2 Table 5.3.2-1)."""
        return cls(
            name="n258",
            n_band=258,
            freq_ghz=26.0,
            scs_khz=120,
            bandwidth_mhz=100.0,
            num_rbs=66,
        )


class AntennaConfig(BaseModel):
    """Antenna array configuration according to 3GPP TR 38.901 Table 7.3-1."""

    model_config = ConfigDict(frozen=True)

    n_rows: int = Field(default=8, ge=1)
    n_cols: int = Field(default=8, ge=1)
    d_v_wavelengths: float = Field(default=0.5, gt=0.0)
    d_h_wavelengths: float = Field(default=0.5, gt=0.0)
    g_element_max_dbi: float = Field(default=8.0)
    mechanical_tilt_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    electrical_tilt_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    electrical_scan_deg: float = Field(default=0.0, ge=-90.0, le=90.0)


class Cell(BaseModel):
    """Individual logical cell operating on a specific band and antenna."""

    model_config = ConfigDict(frozen=True)

    cell_id: str
    cell_type: CellType
    band: NrBand
    antenna: AntennaConfig
    tx_power_dbm: float = Field(..., ge=-30.0, le=65.0)
    cable_loss_db: float = Field(default=0.0, ge=0.0)
    active: bool = True
    source: DataSourceOrigin


class Sector(BaseModel):
    """Radiating sector hosting one or more co-sited cells on the same mast/azimuth."""

    model_config = ConfigDict(frozen=True)

    sector_id: str
    azimuth_deg: float
    ant_height_m: float = Field(..., ge=1.0, le=200.0)
    cells: tuple[Cell, ...]

    @field_validator("azimuth_deg")
    @classmethod
    def _normalize_azimuth(cls, v: float) -> float:
        norm = float(v) % 360.0
        return 0.0 if norm == 0.0 else norm

    @field_validator("cells")
    @classmethod
    def _validate_cells(cls, v: tuple[Cell, ...]) -> tuple[Cell, ...]:
        if not v:
            raise ValueError("Sector must contain at least one Cell")
        return v


class Site(BaseModel):
    """Base station site hosting one or more sectors at a physical 3D location."""

    model_config = ConfigDict(frozen=True)

    site_id: str
    network_alias: str
    x_m: float
    y_m: float
    ground_z_m: float = 0.0
    sectors: tuple[Sector, ...]
    source: DataSourceOrigin

    def tx_position(self, sector: Sector) -> Point3D:
        """Calculate the absolute 3D position of a sector antenna."""
        return Point3D(
            x_m=self.x_m,
            y_m=self.y_m,
            z_m=self.ground_z_m + sector.ant_height_m,
        )
