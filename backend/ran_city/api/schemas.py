"""Pydantic schemas for the FastAPI HTTP boundary in EPSG:4326."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ran_city.data_sources.city_schema import CityZoneSpec, OperatorSpectrumSpec


class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    version: str = "0.1.0"


class AntennaConfigDto(BaseModel):
    """Antenna configuration parameters."""

    model_config = ConfigDict(frozen=True)

    n_rows: int
    n_cols: int
    d_v_wavelengths: float
    d_h_wavelengths: float
    g_element_max_dbi: float
    mechanical_tilt_deg: float
    electrical_tilt_deg: float
    electrical_scan_deg: float


class NrBandDto(BaseModel):
    """5G NR operating band parameters."""

    model_config = ConfigDict(frozen=True)

    name: str
    n_band: int
    freq_ghz: float
    scs_khz: int
    bandwidth_mhz: float
    num_rbs: int


class CellDto(BaseModel):
    """Logical cell with antenna and transmitter parameters."""

    model_config = ConfigDict(frozen=True)

    cell_id: str
    cell_type: str
    band: NrBandDto
    antenna: AntennaConfigDto
    tx_power_dbm: float
    cable_loss_db: float
    active: bool
    source: str


class SectorDto(BaseModel):
    """Radiating sector hosting co-sited cells."""

    model_config = ConfigDict(frozen=True)

    sector_id: str
    azimuth_deg: float
    ant_height_m: float
    cells: list[CellDto]


class SiteDto(BaseModel):
    """Base station site projected to WGS84 coordinates."""

    model_config = ConfigDict(frozen=True)

    site_id: str
    network_alias: str
    lon: float
    lat: float
    x_m: float
    y_m: float
    ground_z_m: float
    source: str
    sectors: list[SectorDto]


class CityResponse(BaseModel):
    """Complete city geographic, operator, and site metadata."""

    model_config = ConfigDict(frozen=True)

    city_id: str
    city_name: str
    bbox_wgs84: tuple[float, float, float, float]
    bbox_utm30: tuple[float, float, float, float]
    zones: list[CityZoneSpec]
    operators: list[OperatorSpectrumSpec]
    sites: list[SiteDto]


class CellOverrideRequest(BaseModel):
    """Cell modification for What-If scenario evaluation."""

    model_config = ConfigDict(frozen=True)

    cell_id: str
    mechanical_tilt_deg: float | None = None
    electrical_tilt_deg: float | None = None
    electrical_scan_deg: float | None = None
    tx_power_dbm: float | None = None
    active: bool | None = None


class SectorOverrideRequest(BaseModel):
    """Sector modification for What-If scenario evaluation."""

    model_config = ConfigDict(frozen=True)

    sector_id: str
    azimuth_deg: float | None = None
    ant_height_m: float | None = None


class CoverageRequest(BaseModel):
    """Request payload to compute and encode a coverage map."""

    model_config = ConfigDict(frozen=True)

    network_alias: str
    n_band: int
    metric: str = "rsrp"  # "rsrp" | "sinr" | "best_server"
    environment: str = "urban"  # "dense_urban" | "urban" | "rural"
    cell_load_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    include_shadow_fading: bool = False
    cell_overrides: list[CellOverrideRequest] = Field(default_factory=list)
    sector_overrides: list[SectorOverrideRequest] = Field(default_factory=list)


class CoverageStats(BaseModel):
    """Statistical summary of the coverage metric over the grid."""

    model_config = ConfigDict(frozen=True)

    min_val: float
    max_val: float
    median_val: float
    p10_val: float
    p90_val: float
    unit: str


class CoverageResponse(BaseModel):
    """Response containing raster base64 data and WGS84 bounding box."""

    model_config = ConfigDict(frozen=True)

    png_base64: str
    bounds_wgs84: tuple[float, float, float, float]
    grid_shape: tuple[int, int]
    resolution_m: float
    stats: CoverageStats


class InspectPointRequest(BaseModel):
    """Request payload to inspect the full 3GPP link budget at a single WGS84 point."""

    model_config = ConfigDict(frozen=True)

    lon: float
    lat: float
    network_alias: str
    n_band: int
    cell_load_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    cell_overrides: list[CellOverrideRequest] = Field(default_factory=list)
    sector_overrides: list[SectorOverrideRequest] = Field(default_factory=list)


class CellInspectionDto(BaseModel):
    """Detailed 3GPP channel and power metrics for a single cell at the inspected point."""

    model_config = ConfigDict(frozen=True)

    cell_id: str
    site_id: str
    d2d_m: float
    d3d_m: float
    zenith_gcs_deg: float
    azimuth_gcs_deg: float
    los_probability: float
    path_loss_db: float
    antenna_gain_dbi: float
    effective_loss_db: float
    rsrp_dbm: float


class InspectPointResponse(BaseModel):
    """Serving cell, co-channel interference, and multicell budget breakdown."""

    model_config = ConfigDict(frozen=True)

    serving_cell_id: str
    serving_rsrp_dbm: float
    sinr_db: float
    noise_per_re_dbm: float
    interference_mw: float
    cells: list[CellInspectionDto]


class AntennaPatternRequest(BaseModel):
    """Request payload to compute horizontal and vertical antenna pattern cuts."""

    model_config = ConfigDict(frozen=True)

    n_rows: int = 8
    n_cols: int = 8
    d_v_wavelengths: float = 0.5
    d_h_wavelengths: float = 0.5
    g_element_max_dbi: float = 8.0
    mechanical_tilt_deg: float = 0.0
    electrical_tilt_deg: float = 0.0
    electrical_scan_deg: float = 0.0
    sector_azimuth_deg: float = 0.0


class AntennaPatternResponse(BaseModel):
    """Computed horizontal and vertical cuts and peak array gain."""

    model_config = ConfigDict(frozen=True)

    azimuth_angles_deg: list[float]
    horizontal_gain_dbi: list[float]
    zenith_angles_deg: list[float]
    vertical_gain_dbi: list[float]
    max_gain_dbi: float
