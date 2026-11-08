# Spec 003: Exportación Ráster WebGL (`PNG`), Motor *What-If* y Adaptador HTTP `FastAPI` (`003-raster-export-and-fastapi-adapter`)

- **Estado**: Aprobado
- **Modalidad de Ejecución**: Flujo SDD en 6 pasos (`Builder Subagent` en `flash` + `Auditor Subagent` read-only + `Main Agent`)
- **Fuentes Curriculares y Arquitectónicas**:
  - Temario 5G RAN: `T1` (*Link Budget puntual y estadístico*) + `T4` (*Cortes polares H/V de antena 3GPP TR 38.901 e impacto What-If de tilts*)
  - Decisiones Arquitectónicas: [ADR 0001](../../docs/brain/decisions/0001-initial-architecture.md) (Hexagonal), [ADR 0002](../../docs/brain/decisions/0002-rf-domain-and-map-guardrails.md) (frontera `EPSG:25830` interna vs `EPSG:4326` en HTTP/UI, transporte `NumPy -> PNG RGBA -> deck.gl BitmapLayer`, prohibición de duplicar lógica 5G en TypeScript)
- **Carril**: `[LANE: SDD]` — Fase 1 (`spec.md`)

---

## 1. Contexto y Propósito

Para aprovechar al máximo la cuota de **Claude Opus 5.5** exclusivamente en la dirección estética (`docs/brain/design.md`) y la construcción visual de los componentes `React + Tailwind + MapLibre GL + deck.gl` (que se abordarán en la `Spec 004`), esta **`Spec 003`** construye y verifica **toda la fontanería técnica, geoespacial y de API** que alimentará la interfaz:

1. **Codificador Ráster `NumPy -> PNG RGBA` (`ran_city.geo.raster`)**:
   - Transforma cualquier matriz 2D $(N_y, N_x)$ de `ScenarioCoverageResult` (`serving_rsrp_dbm`, `sinr_db`, `best_server_idx`) en una imagen `PNG` RGBA ligera en memoria junto con su *bounding box* exacto en `EPSG:4326` (`[west, south, east, north]`), invirtiendo el eje vertical (`np.flipud`) para que la fila superior del `PNG` coincida con el Norte geográfico en `deck.gl BitmapLayer`.
2. **Motor Inmutable de Experimentos *What-If* (`ran_city.radio.whatif`)**:
   - Permite aplicar modificaciones efímeras sobre emplazamientos, sectores y celdas (`mechanical_tilt_deg`, `electrical_tilt_deg`, `electrical_scan_deg`, `tx_power_dbm`, `azimuth_deg`, `active`) devolviendo una nueva colección inmutable de `Site` sin mutar el escenario base cargado desde `data/cities/jaen.yaml`.
3. **Adaptador HTTP `FastAPI` (`ran_city.api`)**:
   - Expone contratos OpenAPI tipados en `EPSG:4326` para consultar la red base de Jaén (`/api/cities/jaen`), recalcular manchas de cobertura ráster con parámetros *What-If* (`/api/cities/jaen/coverage`), inspeccionar el *Link Budget* 3GPP completo en cualquier coordenada `(lon, lat)` (`/api/cities/jaen/inspect-point`) y obtener los diagramas polares horizontal y vertical de un panel 3GPP TR 38.901 (`/api/antenna/pattern`), garantizando que el frontend TypeScript no tenga que implementar ni una sola ecuación física.

---

## 2. Especificación Técnica y Contratos de Frontera

### 2.1 Codificación Ráster `PNG` RGBA y *Bounding Box* WGS84 (`ran_city.geo.raster`)
- **Alineación Norte-Sur (`np.flipud`)**:
  - En `ScenarioGrid` (`EPSG:25830`), la fila `0` es `y_min` (Sur) y la fila `n_y - 1` es `y_max` (Norte).
  - En el sistema de coordenadas de textura de `deck.gl BitmapLayer`, la fila `0` del `PNG` corresponde al borde Norte (`north = lat_max`). El codificador aplica `np.flipud(matrix)` antes de mapear a RGBA `(N_y, N_x, 4)` (`uint8`).
- **Proyección de *Bounding Box***:
  - A partir de `(x_min, y_min, x_max, y_max)` en `EPSG:25830`, se proyectan las 4 esquinas a `EPSG:4326` mediante `utm30_to_wgs84` y se devuelve `bounds_wgs84 = (west, south, east, north)`.
- **Mapeo de color y transparencia**:
  - Soporta rampa continua normalizada en `[vmin, vmax]` (`RSRP`: `[-125.0, -65.0] dBm`; `SINR`: `[-10.0, 30.0] dB`) y paleta categórica para `best_server_idx`.
  - Píxeles no finitos (`NaN`/`inf`) o por debajo de `min_threshold` opcional reciben `alpha = 0` (transparente); los píxeles activos reciben `alpha = 200` (semi-transparente para dejar ver el mapa base).

### 2.2 Motor Inmutable *What-If* (`ran_city.radio.whatif`)
- `CellOverride`: `cell_id: str`, más campos opcionales `mechanical_tilt_deg`, `electrical_tilt_deg`, `electrical_scan_deg`, `tx_power_dbm`, `active`.
- `SectorOverride`: `sector_id: str`, más campos opcionales `azimuth_deg`, `ant_height_m`.
- `apply_whatif_overrides(sites, cell_overrides=(), sector_overrides=()) -> tuple[Site, ...]`:
  - Reconstruye de forma inmutable únicamente los `Site / Sector / Cell` afectados. Si se especifica un `cell_id` o `sector_id` inexistente, lanza `ValueError` explícito.

### 2.3 Endpoints HTTP `FastAPI` (`ran_city.api.app`)
1. `GET /api/health` $\rightarrow$ `{"status": "ok", "version": "0.1.0"}`.
2. `GET /api/cities/{city_id}` $\rightarrow$ Devuelve metadatos de la ciudad (`jaen`), BBox en `EPSG:4326` y `EPSG:25830`, zonas, bloques CNAF (`Red A`, `Red B`, `Red C`) y la lista de `sites` con coordenadas convertidas a `(lon, lat)` (`EPSG:4326`), cota `ground_z_m`, `source` (`estimated` | `synthetic`), sectores y celdas.
3. `POST /api/cities/{city_id}/coverage` $\rightarrow$ Recibe `network_alias`, `n_band`, `metric` (`"rsrp" | "sinr" | "best_server"`), `environment` (`"dense_urban" | "urban" | "rural"`), `cell_load_factor`, `include_shadow_fading` y listas opcionales `cell_overrides` / `sector_overrides`. Devuelve:
   - `png_base64`: cadena `data:image/png;base64,...` lista para pasar a `BitmapLayer(image=...)`.
   - `bounds_wgs84`: `[west, south, east, north]`.
   - `grid_shape`: `[n_y, n_x]` y `resolution_m`.
   - `stats`: `min_val`, `max_val`, `median_val`, `p10_val`, `p90_val` y `unit` (`"dBm"` o `"dB"`).
4. `POST /api/cities/{city_id}/inspect-point` $\rightarrow$ Recibe `lon`, `lat`, `network_alias`, `n_band`, `cell_load_factor` y `cell_overrides`/`sector_overrides`. Evalúa el punto exacto en `EPSG:25830` y devuelve `serving_cell_id`, `serving_rsrp_dbm`, `sinr_db`, `noise_per_re_dbm`, `interference_mw` y el desglose celda a celda (`d2d_m`, `d3d_m`, `zenith_gcs_deg`, `azimuth_gcs_deg`, `los_probability`, `path_loss_db`, `antenna_gain_dbi`, `effective_loss_db`, `rsrp_dbm`).
5. `POST /api/antenna/pattern` $\rightarrow$ Recibe parámetros `AntennaConfig` (`n_rows`, `n_cols`, `mechanical_tilt_deg`, `electrical_tilt_deg`, `electrical_scan_deg`) y `sector_azimuth_deg`. Devuelve los vectores de ganancia `horizontal_cut_dbi` ($\phi \in [0^\circ, 359^\circ]$ en el horizonte $\theta = 90^\circ$) y `vertical_cut_dbi` ($\theta \in [0^\circ, 180^\circ]$ en el azimut principal) junto con la ganancia máxima en `dBi`.

---

## 3. Alcance

### Incluido en `Spec 003`
- Dependencias en `backend/pyproject.toml`: `fastapi>=0.110`, `uvicorn>=0.29`, `pillow>=10.3`.
- Módulo `backend/ran_city/geo/raster.py` (`encode_matrix_png_rgba`, `compute_grid_wgs84_bounds`).
- Módulo `backend/ran_city/radio/whatif.py` (`CellOverride`, `SectorOverride`, `apply_whatif_overrides`).
- Paquete `backend/ran_city/api/` (`schemas.py`, `app.py`) con CORS habilitado para desarrollo local.
- Tests en seams públicos (`test_raster_and_whatif.py` y `test_api_endpoints.py` con `fastapi.testclient.TestClient`).

### Fuera de Alcance (reservado a `Spec 004` con Claude Opus 5.5)
- Creación de `docs/brain/design.md` (entrevista estética con `ui-design`).
- Componentes visuales en `frontend/` (`HTML`, `CSS`, `Tailwind`, `React`, `MapLibre GL`, `deck.gl`) y configuración E2E de Playwright (`Agent Eyes`).

---

## 4. Criterios de Aceptación (CA)

- **CA-1 (Tooling y Aislamiento Hexagonal)**:
  - `backend/.venv/bin/pytest backend/tests`, `backend/.venv/bin/ruff check backend` y `compass check` terminan con salida `0`.
  - `ran_city/{domain,antenna,radio}` sigue sin importar `fastapi`, `PIL`, `rasterio`, `pyproj`, `yaml` ni `httpx`.
- **CA-2 (Codificación Ráster `PNG` RGBA y Orientación Norte-Sur)**:
  - `encode_matrix_png_rgba` genera bytes `PNG` válidos (cabecera `\x89PNG\r\n\x1a\n`) cuyas dimensiones de imagen `(width, height)` coinciden exactamente con `(n_x, n_y)` del `ScenarioGrid`.
  - Un valor máximo situado en el borde Norte de la malla (`y_idx = n_y - 1`) aparece en la fila superior (`row = 0`) de la imagen `PNG` decodificada, y los píxeles `NaN` tienen canal `alpha == 0`.
  - `compute_grid_wgs84_bounds(grid)` devuelve `(west, south, east, north)` en `EPSG:4326` cumpliendo `west < east` y `south < north`.
- **CA-3 (Inmutabilidad del Motor *What-If*)**:
  - `apply_whatif_overrides` modifica `mechanical_tilt_deg`, `electrical_tilt_deg`, `tx_power_dbm`, `active` o `azimuth_deg` en la copia devuelta sin alterar los objetos `Site` originales, y lanza `ValueError` si un `cell_id` o `sector_id` no existe.
- **CA-4 (Contrato HTTP `FastAPI` en `EPSG:4326`)**:
  - `GET /api/cities/jaen` devuelve `200 OK` con los 18 sitios de Jaén proyectados a `lon \in [-3.84, -3.75]` y `lat \in [37.75, 37.81]`, preservando `source` y bandas CNAF.
  - `POST /api/cities/jaen/coverage` devuelve `200 OK` con `png_base64` válido, `bounds_wgs84` y estadísticas coherentes; al enviar un `cell_override` que apaga una celda o incrementa su tilt, la respuesta cambia sin mutar el estado de subsiguientes llamadas sin overrides.
  - `POST /api/cities/jaen/inspect-point` y `POST /api/antenna/pattern` devuelven desgloses físicos completos sin `NaN`s.

---

## 5. Seams Públicos bajo Prueba (Skill `tdd`)

| Seam Público | Qué atrapa (Catches) | Qué no cubre por sí solo (Misses) |
|---|---|---|
| **Seam 1**: `ran_city.geo.raster` (`encode_matrix_png_rgba`, `compute_grid_wgs84_bounds`) | Inversión Norte-Sur del ráster en el mapa, dimensiones `(width, height)` transpuestas, `NaN`s opacos o *bounding box* WGS84 inválido. | Transporte HTTP y serialización JSON. |
| **Seam 2**: `ran_city.radio.whatif` (`apply_whatif_overrides`) | Mutación accidental de la red base en memoria, pérdidas de celdas no tocadas o aceptación silenciosa de IDs inexistentes. | Cálculo de cobertura y API HTTP. |
| **Seam 3**: `ran_city.api.app` (`GET /api/cities/jaen`, `POST /coverage`, `POST /inspect-point`, `POST /antenna/pattern`) | Errores de conversión `EPSG:25830 -> EPSG:4326` en la frontera HTTP, fallos de validación Pydantic o rotura del flujo *What-If* extremo a extremo. | Renderizado WebGL en navegador (`Spec 004`). |
