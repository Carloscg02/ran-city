# Plan Técnico: Spec 002 (`002-sinr-link-budget-and-jaen-gis`)

## 1. Architecture Alignment
- **Capas afectadas**:
  1. **Dominio y Física Pura (`backend/ran_city/{domain,radio}`)**: Extensión de `ScenarioGrid` para relieve 2D (`terrain_z_m`), *shadow fading* 2D correlado en `radio/tr38901.py`, y cálculo de ruido térmico + `SINR` co-canal en `radio/coverage.py`. **Cero dependencias de I/O, red o ficheros GIS** (`NumPy` + `SciPy` + `Pydantic`).
  2. **Adaptadores Geoespaciales y de Datos (`backend/ran_city/{geo,data_sources}`)**: Transformación de coordenadas `EPSG:4326 <-> EPSG:25830` (`pyproj`), muestreo de rasters `MDT05` (`rasterio`), ingesta/fusión OpenCelliD (`MCC=214`) + mástiles OSM y persistencia declarativa en `data/cities/jaen.yaml` (`PyYAML`).
- **Higiene de Credenciales**: La clave `OPENCELLID_API_KEY` proporcionada por el usuario se lee exclusivamente desde variable de entorno / `.env` (gitignored) durante la ejecución del script de ingesta; nunca se escribe en código fuente ni en `data/cities/jaen.yaml`.

## 2. ADR Gate & UI Gate
- **ADR Gate**:
  - Cumple [ADR 0001](../../docs/brain/decisions/0001-initial-architecture.md) (Arquitectura Hexagonal: el núcleo `domain`/`radio` recibe arrays `NumPy` e instancias `Site`, ignorando si vienen de `rasterio`, `jaen.yaml` o un test en memoria).
  - Cumple [ADR 0002](../../docs/brain/decisions/0002-rf-domain-and-map-guardrails.md) (suma de interferencias y ruido estrictamente en `mW`, frontera `EPSG:25830`, separación de operadores en `Red A / Red B / Red C` sobre bloques CNAF y cálculo de `SINR` co-canal aislado por red activa y banda).
  - Cumple [ADR 0003](../../docs/brain/decisions/0003-tr38901-propagation-matrix.md) (extensión de `PropagationMatrix` con *shadow fading* log-normal de `TR 38.901` manteniendo el desacoplo respecto a `G_ant`).
  - No requiere nuevo ADR al materializar decisiones ya aprobadas en `ADR 0001–0003`.
- **UI / Frontend Gate**: No aplica en `Spec 002` (alcance 100% backend Python y datos `data/cities/jaen.yaml`; el *UI Gate* con `docs/brain/design.md` y Playwright `Agent Eyes` se activará en `Spec 003`).

## 3. Diseño de Módulos y Contratos de Seams Públicos

```text
backend/
├── pyproject.toml                 # + scipy, pyproj, rasterio, pyyaml, httpx
├── ran_city/
│   ├── domain/
│   │   ├── units.py               # (Spec 001)
│   │   ├── grid.py                # Seam 1: + terrain_z_m: np.ndarray | None, with_terrain()
│   │   └── models.py              # (Spec 001)
│   ├── antenna/
│   │   └── tr38901.py             # (Spec 001)
│   ├── radio/
│   │   ├── tr38901.py             # Seam 2: + shadow_fading_std_db, decorrelation_distance_m, sample_shadow_fading_map, include_shadow_fading
│   │   └── coverage.py            # Seam 3: + thermal_noise_dbm, re_thermal_noise_dbm, SINR co-canal (interference_mw, sinr_db, network_alias, n_band, cell_load_factor)
│   ├── geo/
│   │   ├── __init__.py
│   │   ├── crs.py                 # Seam 4a: wgs84_to_utm30, utm30_to_wgs84 (EPSG:4326 <-> EPSG:25830)
│   │   └── terrain.py             # Seam 4b: sample_points_elevation, sample_grid_terrain (MDT05 GeoTIFF/COG)
│   └── data_sources/
│       ├── __init__.py
│       ├── city_schema.py         # Seam 5a: CityConfig, CityZoneSpec, OperatorSpectrumSpec, CityScenario, load_city_scenario, save_city_scenario
│       ├── opencellid_osm.py      # Seam 5b: RawCellRecord, OsmMastRecord, map_mnc_to_network_alias, cluster_opencellid_and_snap_osm
│       └── ingest_jaen.py         # CLI / pipeline de descarga y generación de data/cities/jaen.yaml + MDT05 cacheado
├── tests/
│   ├── test_units_and_grid.py     # + tests de ScenarioGrid.with_terrain y geometría 3D con relieve
│   ├── test_domain_models.py
│   ├── test_antenna_tr38901.py
│   ├── test_propagation_tr38901.py# + tests de Shadow Fading 2D correlado (Table 7.4.1-1 y Table 7.5-6)
│   ├── test_coverage_matrices.py  # + tests de ruido térmico por RE, SINR co-canal, aislamiento por red/banda e invariantes Hypothesis
│   ├── test_geo_crs_and_terrain.py# Tests unitarios y de integración con GeoTIFF sintético en EPSG:25830
│   └── test_data_sources_jaen.py  # Tests de clustering OpenCelliD + snap OSM y carga/simulación real de data/cities/jaen.yaml
data/
└── cities/
    └── jaen.yaml                  # Escenario estimado reproducible de Jaén (Red A/B/C, CNAF, cotas MDT05, sitios estimated/synthetic)
```

### Detalle Técnico por Seam

1. **Seam 1 (`ran_city.domain.grid`)**:
   - `ScenarioGrid` incorpora `terrain_z_m: np.ndarray | None = None`.
   - `ScenarioGrid.with_terrain(terrain_z_m: np.ndarray) -> ScenarioGrid`: valida que `terrain_z_m.shape == self.shape` y que todos los valores sean finitos (`np.isfinite`), devolviendo una nueva instancia inmutable.
   - En `geometry_from_tx(tx_pos: Point3D)`: si `terrain_z_m` está presente, usa `z_rx = self.terrain_z_m + self.rx_height_m`; si es `None`, mantiene `z_rx = self.ground_z_m + self.rx_height_m`.

2. **Seam 2 (`ran_city.radio.tr38901`)**:
   - `shadow_fading_std_db(cell_type: CellType, is_los: bool) -> float`: devuelve `4.0 / 6.0` (`MACRO`/`UMa`) y `4.0 / 8.2` (`MICRO` o `PICO`/`UMi`).
   - `decorrelation_distance_m(cell_type: CellType, is_los: bool) -> float`: devuelve `37.0 / 50.0` (`UMa`) y `10.0 / 13.0` (`UMi`).
   - `sample_shadow_fading_map(cell_type: CellType, los_mask: np.ndarray, resolution_m: float, seed: int = 42) -> np.ndarray`: genera los mapas correlados 2D para `LOS` y `NLOS` usando `scipy.ndimage.gaussian_filter` con $\sigma_{\text{px}} = d_{\text{cor}} / \Delta_{\text{grid}}$, renormaliza dividiendo por la norma $L_2$ del kernel discreto 2D para preservar varianza unitaria exacta, escala por $\sigma_{\text{SF}}$ y selecciona píxel a píxel según `los_mask`.
   - `PropagationMatrix` añade el campo `shadow_fading_db: np.ndarray` (ceros cuando `include_shadow_fading=False`), y `compute_propagation_matrix` añade `include_shadow_fading: bool = False` y `resolution_m: float = 12.0`.

3. **Seam 3 (`ran_city.radio.coverage`)**:
   - `BOLTZMANN_K_J_K: float = 1.380649e-23`.
   - `thermal_noise_dbm(bandwidth_hz: float, noise_figure_db: float = 9.0, temperature_k: float = 290.0) -> Dbm`.
   - `re_thermal_noise_dbm(band: NrBand, noise_figure_db: float = 9.0, temperature_k: float = 290.0) -> Dbm`: evalúa `thermal_noise_dbm(band.scs_khz * 1000.0, noise_figure_db, temperature_k)`.
   - `ScenarioCoverageResult` añade:
     - `noise_per_re_dbm: float`
     - `interference_mw: np.ndarray` (suma lineal en `mW` de las celdas co-canal interferentes $j \neq k^*(y, x)$)
     - `sinr_db: np.ndarray` ($10\log_{10}(S_{k^*} / (I + N_{\text{RE}}))$)
   - `compute_scenario_coverage` añade:
     - `network_alias: str | None = None`: filtra sitios por operador antes de calcular; si en las celdas seleccionadas quedan mezclados distintos `network_alias` o distintas bandas `n_band`, lanza `ValueError` explícito para impedir errores físicos de sumar interferencia entre operadores o bandas ortogonales.
     - `n_band: int | None = None`: filtra celdas activas por banda NR (`28`, `78`, `258`).
     - `ue_noise_figure_db: float = 9.0`, `temperature_k: float = 290.0`, `cell_load_factor: float = 1.0` ($\eta \in [0, 1]$) e `include_shadow_fading: bool = False`.

4. **Seam 4 (`ran_city.geo.crs` & `ran_city.geo.terrain`)**:
   - `wgs84_to_utm30(lon, lat)` y `utm30_to_wgs84(x_m, y_m)`: basadas en `pyproj.Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)` cacheado a nivel de módulo, aceptando escalares o `np.ndarray`.
   - `sample_points_elevation(raster_path: Path, xs_m: Sequence[float], ys_m: Sequence[float]) -> np.ndarray`: lee elevaciones en metros sobre un GeoTIFF/COG en `EPSG:25830` con `rasterio`.
   - `sample_grid_terrain(raster_path: Path, grid: ScenarioGrid) -> ScenarioGrid`: muestrea la ventana del GeoTIFF sobre los centros `(xx_m, yy_m)` del `ScenarioGrid` y devuelve `grid.with_terrain(terrain_z_m)`.

5. **Seam 5 (`ran_city.data_sources`)**:
   - `map_mnc_to_network_alias(mnc: int) -> str | None`: mapea los MNC principales españoles (`7 -> "Red A"`, `1 -> "Red B"`, `3 -> "Red C"`).
   - `cluster_opencellid_and_snap_osm(cells: Sequence[RawCellRecord], masts: Sequence[OsmMastRecord], ...)`: agrupa celdas por operador y proximidad en `EPSG:25830`, aplica *snap* al mástil OSM más cercano si está a $\le 75\text{ m}$, construye sectores y celdas con sus bandas CNAF (`n28`, `n78`) y asigna `source=DataSourceOrigin.ESTIMATED`.
   - `ingest_jaen.py`: descarga los datos de Jaén desde OpenCelliD (usando `OPENCELLID_API_KEY`), Overpass API (mástiles OSM de Jaén) y CNIG WCS/COG `MDT05` (con respaldo sintético de elevación/nodos si algún servicio externo falla temporalmente), y escribe `data/cities/jaen.yaml`.

## 4. Estrategia de Ejecución Pedagógica (Modo 2 + `subagent-fast`)
- **Tarea 1 (Dependencias y Seam 1 — Relieve 3D en `ScenarioGrid`)**: Explicación del impacto geométrico de $Z_{\text{terrain}}(y, x)$ sobre $D_{3\text{D}}$ y $\Theta_{\text{GCS}}$ y ciclo `RED -> GREEN`.
- **Tarea 2 (Seam 2 — *Shadow Fading* 2D Correlado `TR 38.901`)**: Revisión línea a línea de la normalización del filtro espacial 2D ($\|\mathbf{K}\|_2$) y valores de `Table 7.4.1-1` / `Table 7.5-6`.
- **Tarea 3 (Seam 3 — Ruido Térmico por `RE` y `SINR` Co-Canal en `mW`)**: Revisión línea a línea de la ecuación de ruido por subportadora, aislamiento co-canal intra-operador y suma lineal en `mW`.
- **Tarea 4 (Seam 4 — Adaptador `ran_city.geo`: `EPSG:25830` y `MDT05`)**: Delegada en el subagente rápido (`flash`) con verificación estricta en `pytest`.
- **Tarea 5 (Seam 5 — Ingesta OpenCelliD `MCC=214` + OSM + generación de `data/cities/jaen.yaml`)**: Ejecución del pipeline con la API key en variable de entorno, generación de `data/cities/jaen.yaml` y test de integración extremo a extremo calculando `RSRP` y `SINR` sobre Jaén.
