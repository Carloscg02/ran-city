# Plan Técnico: Spec 003 (`003-raster-export-and-fastapi-adapter`)

## 1. Architecture Alignment
- **Capas afectadas**:
  1. **Dominio Radio (`backend/ran_city/radio/whatif.py`)**: Funciones puras de transformación inmutable de topología (`Site -> Sector -> Cell`) para experimentos *What-If*. Cero dependencias externas.
  2. **Adaptador Geoespacial de Salida (`backend/ran_city/geo/raster.py`)**: Codificación de matrices `NumPy` 2D a `PNG` RGBA (`Pillow`) y cálculo de *bounding box* WGS84 (`EPSG:4326`).
  3. **Adaptador Primario HTTP (`backend/ran_city/api/`)**: Aplicación `FastAPI` fina que orquesta `load_city_scenario`, `apply_whatif_overrides`, `compute_scenario_coverage`, `encode_matrix_png_rgba` y `compute_antenna_gain_matrix`, exponiendo toda la física 3GPP lista para que el frontend de la `Spec 004` sea puramente declarativo y visual.

## 2. ADR Gate & UI Gate
- **ADR Gate**:
  - Materializa directamente [ADR 0001](../../docs/brain/decisions/0001-initial-architecture.md) y [ADR 0002](../../docs/brain/decisions/0002-rf-domain-and-map-guardrails.md) (`EPSG:25830` en cálculo interno, `EPSG:4326` en la frontera HTTP, y transporte de rejillas como rasters `PNG` RGBA con *bounding box* WGS84 en lugar de polígonos GeoJSON).
- **UI / Frontend Gate**:
  - No se escribe ningún archivo visual (`HTML`, `CSS`, `Tailwind`, `React`) en esta `Spec 003`, reservando intacta la entrevista estética de `docs/brain/design.md` y la creación de componentes visuales para la sesión con **Claude Opus 5.5** en la `Spec 004`.

## 3. Diseño de Módulos y Contratos de Seams Públicos

```text
backend/
├── pyproject.toml                 # + fastapi, uvicorn, pillow
├── ran_city/
│   ├── radio/
│   │   └── whatif.py              # Seam 2: CellOverride, SectorOverride, apply_whatif_overrides
│   ├── geo/
│   │   └── raster.py              # Seam 1: RasterOverlay, compute_grid_wgs84_bounds, encode_matrix_png_rgba
│   └── api/
│       ├── __init__.py
│       ├── schemas.py             # Modelos Pydantic de frontera HTTP (WGS84, estadísticas, point inspect, antenna cuts)
│       └── app.py                 # Seam 3: create_app() FastAPI con /api/health, /api/cities/{city_id}, /coverage, /inspect-point, /antenna/pattern
└── tests/
    ├── test_raster_and_whatif.py  # Tests unitarios y de propiedades Hypothesis para Seam 1 y Seam 2
    └── test_api_endpoints.py      # Tests de integración HTTP con TestClient para Seam 3
```

### Detalle Técnico por Seam

1. **Seam 1 (`ran_city.geo.raster`)**:
   - `compute_grid_wgs84_bounds(grid: ScenarioGrid) -> tuple[float, float, float, float]`:
     - Proyecta las 4 esquinas `(x_min, y_min)`, `(x_max, y_min)`, `(x_min, y_max)`, `(x_max, y_max)` de `EPSG:25830` a `EPSG:4326` con `utm30_to_wgs84` y devuelve `(west, south, east, north)`.
   - `encode_matrix_png_rgba(matrix: np.ndarray, vmin: float, vmax: float, alpha: int = 200, min_threshold: float | None = None, categorical: bool = False) -> bytes`:
     - Invierte verticalmente con `np.flipud(matrix)` para que la fila `0` del `PNG` sea el Norte (`y_max`).
     - Aplica una rampa científica de 5 paradas (azul profundo $\rightarrow$ cian $\rightarrow$ verde $\rightarrow$ ámbar $\rightarrow$ rojo/magenta) vectorizada en `NumPy` para métricas continuas (`RSRP`, `SINR`), o una paleta diferenciada para `categorical=True` (`best_server_idx`), codificando en `PNG` RGBA mediante `PIL.Image` en un `io.BytesIO`.

2. **Seam 2 (`ran_city.radio.whatif`)**:
   - `CellOverride` y `SectorOverride` (`dataclass(frozen=True, slots=True)`).
   - `apply_whatif_overrides(sites: Sequence[Site], cell_overrides: Sequence[CellOverride] = (), sector_overrides: Sequence[SectorOverride] = ()) -> tuple[Site, ...]`:
     - Recorre `sites` creando copias actualizadas con `model_copy(update=...)` únicamente donde coincida `sector_id` o `cell_id`. Verifica que todos los IDs solicitados existan en el escenario (lanzando `ValueError` si algún ID no se encuentra).

3. **Seam 3 (`ran_city.api.app` & `schemas.py`)**:
   - Carga y cachea en memoria `data/cities/jaen.yaml`.
   - `GET /api/cities/{city_id}`: transforma `(site.x_m, site.y_m)` a `(lon, lat)` con `utm30_to_wgs84`.
   - `POST /api/cities/{city_id}/coverage`: aplica `apply_whatif_overrides`, construye el `ScenarioGrid` (por defecto `URBAN` a `12 m` o el entorno solicitado, permitiendo un recorte de BBox opcional para zoom rápido), ejecuta `compute_scenario_coverage` con `los_mask_override=True` (o estocástico por semilla) y devuelve el `PNG` en Base64 data URL junto a `bounds_wgs84` y estadísticas (`min`, `max`, `median`, `p10`, `p90`).
   - `POST /api/cities/{city_id}/inspect-point`: convierte `(lon, lat)` a `(x_m, y_m)` en `EPSG:25830`, evalúa una malla puntual `1x1` centrada en ese punto con la cota hipsométrica local de Jaén y devuelve el presupuesto de enlace completo de la celda servidora y todas las celdas interferentes co-canal.
   - `POST /api/antenna/pattern`: evalúa vectorialmente `panel_gain_dbi` y `gcs_to_lcs_angles` para los cortes H ($\phi \in [0^\circ, 359^\circ], \theta = 90^\circ$) y V ($\theta \in [0^\circ, 180^\circ], \phi = \phi_{\text{sector}}$).
