"""FastAPI application factory and endpoints for RAN-city."""

from __future__ import annotations

import base64
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ran_city.antenna.tr38901 import gcs_to_lcs_angles, panel_gain_dbi
from ran_city.api.schemas import (
    AntennaConfigDto,
    AntennaPatternRequest,
    AntennaPatternResponse,
    CellDto,
    CellInspectionDto,
    CityResponse,
    CoverageRequest,
    CoverageResponse,
    CoverageStats,
    HealthResponse,
    InspectPointRequest,
    InspectPointResponse,
    NrBandDto,
    SectorDto,
    SiteDto,
)
from ran_city.data_sources.city_schema import CityScenario, load_city_scenario
from ran_city.domain.grid import EnvironmentType, GridGeometry, ScenarioGrid
from ran_city.domain.models import AntennaConfig, Cell, Sector, Site
from ran_city.geo.crs import utm30_to_wgs84, wgs84_to_utm30
from ran_city.geo.raster import compute_grid_wgs84_bounds, encode_matrix_png_rgba
from ran_city.radio.coverage import (
    compute_cell_coverage,
    compute_scenario_coverage,
    re_thermal_noise_dbm,
)
from ran_city.radio.tr38901 import compute_propagation_matrix
from ran_city.radio.whatif import CellOverride, SectorOverride, apply_whatif_overrides

_SCENARIO_CACHE: dict[str, CityScenario] = {}


def _get_project_root() -> Path:
    """Locate the root directory of RAN-city project."""
    # backend/ran_city/api/app.py -> parent x 4 is repo root
    return Path(__file__).resolve().parent.parent.parent.parent


def get_city_scenario(city_id: str) -> CityScenario:
    """Retrieve and cache in memory the CityScenario for a given city ID."""
    if city_id in _SCENARIO_CACHE:
        return _SCENARIO_CACHE[city_id]

    yaml_file = _get_project_root() / "data" / "cities" / f"{city_id}.yaml"
    if not yaml_file.exists():
        raise HTTPException(status_code=404, detail=f"City '{city_id}' not found")

    scenario = load_city_scenario(yaml_file)
    _SCENARIO_CACHE[city_id] = scenario
    return scenario


def _to_site_dto(site: Site) -> SiteDto:
    lon, lat = utm30_to_wgs84(site.x_m, site.y_m)
    sector_dtos: list[SectorDto] = []

    for sec in site.sectors:
        cell_dtos: list[CellDto] = []
        for c in sec.cells:
            cell_dtos.append(
                CellDto(
                    cell_id=c.cell_id,
                    cell_type=c.cell_type.value,
                    band=NrBandDto(
                        name=c.band.name,
                        n_band=c.band.n_band,
                        freq_ghz=c.band.freq_ghz,
                        scs_khz=c.band.scs_khz,
                        bandwidth_mhz=c.band.bandwidth_mhz,
                        num_rbs=c.band.num_rbs,
                    ),
                    antenna=AntennaConfigDto(
                        n_rows=c.antenna.n_rows,
                        n_cols=c.antenna.n_cols,
                        d_v_wavelengths=c.antenna.d_v_wavelengths,
                        d_h_wavelengths=c.antenna.d_h_wavelengths,
                        g_element_max_dbi=c.antenna.g_element_max_dbi,
                        mechanical_tilt_deg=c.antenna.mechanical_tilt_deg,
                        electrical_tilt_deg=c.antenna.electrical_tilt_deg,
                        electrical_scan_deg=c.antenna.electrical_scan_deg,
                    ),
                    tx_power_dbm=c.tx_power_dbm,
                    cable_loss_db=c.cable_loss_db,
                    active=c.active,
                    source=c.source.value,
                )
            )
        sector_dtos.append(
            SectorDto(
                sector_id=sec.sector_id,
                azimuth_deg=sec.azimuth_deg,
                ant_height_m=sec.ant_height_m,
                cells=cell_dtos,
            )
        )

    return SiteDto(
        site_id=site.site_id,
        network_alias=site.network_alias,
        lon=float(lon),
        lat=float(lat),
        x_m=site.x_m,
        y_m=site.y_m,
        ground_z_m=site.ground_z_m,
        source=site.source.value,
        sectors=sector_dtos,
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="RAN-city 5G API",
        version="0.1.0",
        description="REST and raster WebGL adapter for 5G NR physical simulation",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def get_health() -> HealthResponse:
        return HealthResponse(status="ok", version="0.1.0")

    @app.get("/api/cities/{city_id}", response_model=CityResponse)
    def get_city(city_id: str) -> CityResponse:
        scenario = get_city_scenario(city_id)
        site_dtos = [_to_site_dto(s) for s in scenario.sites]
        return CityResponse(
            city_id=scenario.config.city_id,
            city_name=scenario.config.city_name,
            bbox_wgs84=scenario.config.bbox_wgs84,
            bbox_utm30=scenario.config.bbox_utm30,
            zones=scenario.config.zones,
            operators=scenario.config.operators,
            sites=site_dtos,
        )

    @app.post("/api/cities/{city_id}/coverage", response_model=CoverageResponse)
    def post_city_coverage(city_id: str, req: CoverageRequest) -> CoverageResponse:
        scenario = get_city_scenario(city_id)

        cell_overrides = [
            CellOverride(
                cell_id=c.cell_id,
                mechanical_tilt_deg=c.mechanical_tilt_deg,
                electrical_tilt_deg=c.electrical_tilt_deg,
                electrical_scan_deg=c.electrical_scan_deg,
                tx_power_dbm=c.tx_power_dbm,
                active=c.active,
            )
            for c in req.cell_overrides
        ]
        sector_overrides = [
            SectorOverride(
                sector_id=s.sector_id,
                azimuth_deg=s.azimuth_deg,
                ant_height_m=s.ant_height_m,
            )
            for s in req.sector_overrides
        ]

        try:
            modified_sites = apply_whatif_overrides(
                scenario.sites,
                cell_overrides=cell_overrides,
                sector_overrides=sector_overrides,
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

        try:
            env_type = EnvironmentType(req.environment)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid environment '{req.environment}'")

        min_x, min_y, max_x, max_y = scenario.config.bbox_utm30
        grid = ScenarioGrid.from_bounds(
            x_min=min_x,
            y_min=min_y,
            x_max=max_x,
            y_max=max_y,
            environment=env_type,
        )

        try:
            coverage = compute_scenario_coverage(
                sites=modified_sites,
                grid=grid,
                los_mask_override=True,
                network_alias=req.network_alias,
                n_band=req.n_band,
                cell_load_factor=req.cell_load_factor,
                include_shadow_fading=req.include_shadow_fading,
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

        metric_name = req.metric.lower()
        if metric_name == "rsrp":
            matrix = coverage.serving_rsrp_dbm
            vmin, vmax = -125.0, -65.0
            min_threshold = -140.0
            categorical = False
            unit = "dBm"
        elif metric_name == "sinr":
            matrix = coverage.sinr_db
            vmin, vmax = -10.0, 30.0
            min_threshold = -30.0
            categorical = False
            unit = "dB"
        elif metric_name == "best_server":
            matrix = coverage.best_server_idx.astype(np.float64)
            vmin, vmax = 0.0, float(max(len(coverage.cell_ids) - 1, 1))
            min_threshold = None
            categorical = True
            unit = "index"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported metric '{req.metric}'")

        png_bytes = encode_matrix_png_rgba(
            matrix,
            vmin=vmin,
            vmax=vmax,
            alpha=200,
            min_threshold=min_threshold,
            categorical=categorical,
        )
        png_base64 = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
        bounds_wgs84 = compute_grid_wgs84_bounds(grid)

        finite_vals = matrix[np.isfinite(matrix)]
        if len(finite_vals) > 0:
            min_val = float(np.min(finite_vals))
            max_val = float(np.max(finite_vals))
            median_val = float(np.median(finite_vals))
            p10_val = float(np.percentile(finite_vals, 10))
            p90_val = float(np.percentile(finite_vals, 90))
        else:
            min_val = max_val = median_val = p10_val = p90_val = 0.0

        return CoverageResponse(
            png_base64=png_base64,
            bounds_wgs84=bounds_wgs84,
            grid_shape=grid.shape,
            resolution_m=grid.environment.resolution_m,
            stats=CoverageStats(
                min_val=min_val,
                max_val=max_val,
                median_val=median_val,
                p10_val=p10_val,
                p90_val=p90_val,
                unit=unit,
            ),
        )

    @app.post("/api/cities/{city_id}/inspect-point", response_model=InspectPointResponse)
    def post_inspect_point(city_id: str, req: InspectPointRequest) -> InspectPointResponse:
        scenario = get_city_scenario(city_id)

        cell_overrides = [
            CellOverride(
                cell_id=c.cell_id,
                mechanical_tilt_deg=c.mechanical_tilt_deg,
                electrical_tilt_deg=c.electrical_tilt_deg,
                electrical_scan_deg=c.electrical_scan_deg,
                tx_power_dbm=c.tx_power_dbm,
                active=c.active,
            )
            for c in req.cell_overrides
        ]
        sector_overrides = [
            SectorOverride(
                sector_id=s.sector_id,
                azimuth_deg=s.azimuth_deg,
                ant_height_m=s.ant_height_m,
            )
            for s in req.sector_overrides
        ]

        try:
            modified_sites = apply_whatif_overrides(
                scenario.sites,
                cell_overrides=cell_overrides,
                sector_overrides=sector_overrides,
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

        x_rx, y_rx = wgs84_to_utm30(req.lon, req.lat)

        active_cells: list[tuple[Site, Sector, Cell]] = []
        for site in modified_sites:
            if site.network_alias != req.network_alias:
                continue
            for sector in site.sectors:
                for cell in sector.cells:
                    if not cell.active:
                        continue
                    if cell.band.n_band != req.n_band:
                        continue
                    active_cells.append((site, sector, cell))

        if not active_cells:
            raise HTTPException(
                status_code=400,
                detail=f"No active cells found for operator '{req.network_alias}' and band {req.n_band}",
            )

        rx_height_m = 1.5
        inspections: list[CellInspectionDto] = []

        for site, sector, cell in active_cells:
            tx_pos = site.tx_position(sector)
            dx = float(x_rx) - tx_pos.x_m
            dy = float(y_rx) - tx_pos.y_m
            d2d_m = float(np.hypot(dx, dy))
            rx_z = float(site.ground_z_m) + rx_height_m
            dz = rx_z - tx_pos.z_m
            raw_d3d = float(np.hypot(d2d_m, dz))
            d3d_m = max(raw_d3d, 1.0)

            cos_zenith = float(np.clip(dz / d3d_m, -1.0, 1.0))
            zenith_gcs_deg = float(np.degrees(np.arccos(cos_zenith)))
            azimuth_gcs_deg = float(np.degrees(np.arctan2(dx, dy)) % 360.0)

            geom = GridGeometry(
                d2d_m=np.array([[d2d_m]]),
                d3d_m=np.array([[d3d_m]]),
                zenith_gcs_deg=np.array([[zenith_gcs_deg]]),
                azimuth_gcs_deg=np.array([[azimuth_gcs_deg]]),
            )

            prop = compute_propagation_matrix(
                cell_type=cell.cell_type,
                freq_ghz=cell.band.freq_ghz,
                h_bs_m=sector.ant_height_m,
                h_ut_m=rx_height_m,
                grid_geom=geom,
                seed=42,
                los_mask=np.array([[True]]),
                include_shadow_fading=False,
            )

            cov = compute_cell_coverage(
                cell=cell,
                sector_azimuth_deg=sector.azimuth_deg,
                grid_geom=geom,
                prop_matrix=prop,
            )

            inspections.append(
                CellInspectionDto(
                    cell_id=cell.cell_id,
                    site_id=site.site_id,
                    d2d_m=round(d2d_m, 2),
                    d3d_m=round(d3d_m, 2),
                    zenith_gcs_deg=round(zenith_gcs_deg, 2),
                    azimuth_gcs_deg=round(azimuth_gcs_deg, 2),
                    los_probability=round(float(prop.pr_los[0, 0]), 4),
                    path_loss_db=round(float(prop.loss_db[0, 0]), 2),
                    antenna_gain_dbi=round(float(cov.antenna_gain_dbi[0, 0]), 2),
                    effective_loss_db=round(float(cov.effective_loss_db[0, 0]), 2),
                    rsrp_dbm=round(float(cov.rsrp_dbm[0, 0]), 2),
                )
            )

        best_cell = max(inspections, key=lambda c: c.rsrp_dbm)
        serving_cell_id = best_cell.cell_id
        serving_rsrp_dbm = best_cell.rsrp_dbm

        ref_cell = active_cells[0][2]
        noise_dbm = re_thermal_noise_dbm(ref_cell.band).value
        noise_mw = 10.0 ** (noise_dbm / 10.0)

        serving_mw = 10.0 ** (serving_rsrp_dbm / 10.0)
        non_serving_mw = sum(
            10.0 ** (c.rsrp_dbm / 10.0) for c in inspections if c.cell_id != serving_cell_id
        )
        interference_mw = float(req.cell_load_factor) * non_serving_mw
        sinr_linear = serving_mw / (interference_mw + noise_mw)
        sinr_db = float(10.0 * np.log10(sinr_linear))

        return InspectPointResponse(
            serving_cell_id=serving_cell_id,
            serving_rsrp_dbm=round(serving_rsrp_dbm, 2),
            sinr_db=round(sinr_db, 2),
            noise_per_re_dbm=round(noise_dbm, 2),
            interference_mw=float(interference_mw),
            cells=inspections,
        )

    @app.post("/api/antenna/pattern", response_model=AntennaPatternResponse)
    def post_antenna_pattern(req: AntennaPatternRequest) -> AntennaPatternResponse:
        antenna = AntennaConfig(
            n_rows=req.n_rows,
            n_cols=req.n_cols,
            d_v_wavelengths=req.d_v_wavelengths,
            d_h_wavelengths=req.d_h_wavelengths,
            g_element_max_dbi=req.g_element_max_dbi,
            mechanical_tilt_deg=req.mechanical_tilt_deg,
            electrical_tilt_deg=req.electrical_tilt_deg,
            electrical_scan_deg=req.electrical_scan_deg,
        )

        azimuth_angles_deg = np.arange(360, dtype=float)
        zenith_h = np.full(360, 90.0, dtype=float)
        zenith_lcs_h, azimuth_lcs_h = gcs_to_lcs_angles(
            zenith_h,
            azimuth_angles_deg,
            sector_azimuth_deg=req.sector_azimuth_deg,
            mechanical_tilt_deg=req.mechanical_tilt_deg,
        )
        h_gain = np.asarray(panel_gain_dbi(zenith_lcs_h, azimuth_lcs_h, antenna), dtype=float)

        zenith_angles_deg = np.arange(181, dtype=float)
        azimuth_v = np.full(181, float(req.sector_azimuth_deg), dtype=float)
        zenith_lcs_v, azimuth_lcs_v = gcs_to_lcs_angles(
            zenith_angles_deg,
            azimuth_v,
            sector_azimuth_deg=req.sector_azimuth_deg,
            mechanical_tilt_deg=req.mechanical_tilt_deg,
        )
        v_gain = np.asarray(panel_gain_dbi(zenith_lcs_v, azimuth_lcs_v, antenna), dtype=float)

        max_gain = float(np.max(np.concatenate([h_gain, v_gain])))

        return AntennaPatternResponse(
            azimuth_angles_deg=[float(x) for x in azimuth_angles_deg],
            horizontal_gain_dbi=[round(float(x), 2) for x in h_gain],
            zenith_angles_deg=[float(x) for x in zenith_angles_deg],
            vertical_gain_dbi=[round(float(x), 2) for x in v_gain],
            max_gain_dbi=round(max_gain, 2),
        )

    return app
