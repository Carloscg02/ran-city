# Módulo Funcional: Exportación Ráster WebGL, Sandbox What-If y API FastAPI (`raster-whatif-and-fastapi-adapter`)

> Capa de transformación inmutable *What-If*, codificación ráster `NumPy -> PNG RGBA` para `deck.gl BitmapLayer` y adaptador HTTP `FastAPI` en `EPSG:4326`.

## 1. Motor Inmutable de Experimentos *What-If* (`backend/ran_city/radio/whatif.py`)
- **`CellOverride` y `SectorOverride`**: Especificaciones inmutables de cambios sobre tilts (`mechanical_tilt_deg`, `electrical_tilt_deg`, `electrical_scan_deg`), potencia (`tx_power_dbm`), estado (`active`), orientación (`azimuth_deg`) y altura (`ant_height_m`).
- **`apply_whatif_overrides`**: Aplica overrides sobre una secuencia de `Site` devolviendo una nueva tupla inmutable sin mutar el escenario base en memoria, permitiendo *Reset* instantáneo.

## 2. Codificador Ráster `PNG` RGBA (`backend/ran_city/geo/raster.py`)
- **`compute_grid_wgs84_bounds`**: Proyecta los bordes métricos `EPSG:25830` de `ScenarioGrid` a `(west, south, east, north)` en `EPSG:4326`.
- **`encode_matrix_png_rgba`**: Invierte verticalmente (`np.flipud`) la matriz 2D para alinear el borde Norte con la fila `0` de `deck.gl BitmapLayer`, normaliza rangos continuos (`RSRP`, `SINR`) o categóricos (`best_server_idx`) y asigna `alpha=0` a `NaN`s o valores bajo umbral.

## 3. Adaptador HTTP `FastAPI` (`backend/ran_city/api/`)
- **`app.py` (`create_app`) y `schemas.py`**:
  - `GET /api/health`
  - `GET /api/cities/{city_id}` (sitios proyectados a `EPSG:4326`, zonas, bloques CNAF y trazabilidad `source`).
  - `POST /api/cities/{city_id}/coverage` (`png_base64` data URL, `bounds_wgs84`, estadísticas `min/max/median/p10/p90` y soporte de overrides *What-If*).
  - `POST /api/cities/{city_id}/inspect-point` (desglose 3GPP celda a celda en cualquier coordenada `(lon, lat)`).
  - `POST /api/antenna/pattern` (cortes polares horizontal `0°..359°` y vertical `0°..180°` en `dBi` según `TR 38.901`).

## 4. Suite de Verificación
- `backend/tests/test_raster_and_whatif.py`
- `backend/tests/test_api_endpoints.py`
