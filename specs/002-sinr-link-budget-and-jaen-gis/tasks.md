# Tareas de Implementación: Spec 002 (`002-sinr-link-budget-and-jaen-gis`)

> Ciclo estricto `RED -> GREEN -> REFACTOR` en Modo 2 (Co-implementación guiada para dominio 5G y `subagent-fast` para adaptadores GIS). Toda tarea completada `[x]` debe registrar su bloque de `Prueba Observada:` real.

- [x] Tarea 1: Actualizar dependencias (`pyproject.toml`) y Seam 1 — Soporte de relieve 2D (`terrain_z_m` y `with_terrain`) en `ScenarioGrid` (`ran_city.domain.grid`).
  - Añadir `scipy>=1.12`, `pyproj>=3.6`, `rasterio>=1.3`, `pyyaml>=6.0` y `httpx>=0.27` en `backend/pyproject.toml` e instalar en `backend/.venv`.
  - Ciclo `RED -> GREEN` en `test_units_and_grid.py` y `grid.py` verificando que `ScenarioGrid.with_terrain(terrain_z_m)` valida dimensiones y finitud, y que `geometry_from_tx` actualiza correctamente $D_{3\text{D}}$ y el ángulo cenital 3GPP $\Theta_{\text{GCS}}$ sobre terreno con desnivel.
  - **Prueba Observada**:
    ```text
    backend/.venv/bin/pytest backend/tests/test_units_and_grid.py
    ============================== 12 passed in 0.29s ==============================
    backend/.venv/bin/pytest backend/tests && backend/.venv/bin/ruff check backend
    ============================== 40 passed in 0.63s ==============================
    All checks passed!
    ```

- [x] Tarea 2: Seam 2 — *Shadow Fading* log-normal espacialmente correlado en 2D (`ran_city.radio.tr38901`, `Table 7.4.1-1` y `Table 7.5-6`).
  - Ciclo `RED -> GREEN` en `test_propagation_tr38901.py` y `radio/tr38901.py` para `shadow_fading_std_db`, `decorrelation_distance_m`, `sample_shadow_fading_map` (con renormalización analítica de varianza $\|\mathbf{K}\|_2$ tras filtro espacial 2D) e integración opcional `include_shadow_fading` en `compute_propagation_matrix`.
  - **Prueba Observada**:
    ```text
    backend/.venv/bin/pytest backend/tests/test_propagation_tr38901.py
    ============================== 15 passed in 0.54s ==============================
    backend/.venv/bin/pytest backend/tests && backend/.venv/bin/ruff check backend
    ============================== 45 passed in 0.70s ==============================
    All checks passed!
    ```

- [x] Tarea 3: Seam 3 — Ruido térmico $k_B T_0 B F$ por `RE` y `SINR` co-canal multicelda en `mW` (`ran_city.radio.coverage`).
  - Ciclo `RED -> GREEN` en `test_coverage_matrices.py` y `radio/coverage.py` para `thermal_noise_dbm`, `re_thermal_noise_dbm` y extensión de `compute_scenario_coverage` con suma lineal de interferencia co-canal en `mW`, filtrado por `network_alias` y `n_band`, factor de carga `cell_load_factor` y propiedades `hypothesis` de monotonía y cota `SINR <= SNR`.
  - **Prueba Observada**:
    ```text
    backend/.venv/bin/pytest backend/tests/test_coverage_matrices.py
    ============================== 11 passed in 0.59s ==============================
    backend/.venv/bin/pytest backend/tests && backend/.venv/bin/ruff check backend
    ============================== 52 passed in 0.85s ==============================
    All checks passed!
    ```

- [x] Tarea 4: Seam 4 — Adaptador geoespacial `ran_city.geo` (proyección `EPSG:4326 <-> EPSG:25830` en `crs.py` y lectura de relieve `MDT05` en `terrain.py`).
  - Ciclo `RED -> GREEN` en `test_geo_crs_and_terrain.py`, `geo/crs.py` y `geo/terrain.py` comprobando biyectividad `WGS84 <-> UTM 30N` en las coordenadas de Jaén (con `hypothesis`) y muestreo de elevaciones desde un GeoTIFF en `EPSG:25830` hacia sitios y `ScenarioGrid`.
  - **Prueba Observada**:
    ```text
    backend/.venv/bin/pytest backend/tests/test_geo_crs_and_terrain.py
    ============================== 6 passed in 0.82s ===============================
    backend/.venv/bin/pytest backend/tests && backend/.venv/bin/ruff check backend
    ============================== 58 passed in 1.06s ==============================
    All checks passed!
    ```

- [x] Tarea 5: Seam 5 — Adaptador `ran_city.data_sources` (clustering OpenCelliD `MCC=214` + *snap* a mástiles OSM + esquema YAML) y generación real de `data/cities/jaen.yaml`.
  - Ciclo `RED -> GREEN` en `test_data_sources_jaen.py`, `city_schema.py`, `opencellid_osm.py` e `ingest_jaen.py`.
  - Ejecutar la ingesta sobre el BBox de Jaén usando `OPENCELLID_API_KEY` en variable de entorno + Overpass OSM + relieve `MDT05`, persistir `data/cities/jaen.yaml` con emplazamientos `estimated` (`Red A`, `Red B`, `Red C` sobre bloques CNAF `n28`/`n78`) y verificar la simulación multicelda `RSRP` + `SINR` del escenario de Jaén sin conexión.
  - **Prueba Observada**:
    ```text
    backend/.venv/bin/pytest backend/tests/test_data_sources_jaen.py
    ============================== 5 passed in 0.85s ===============================
    backend/.venv/bin/pytest backend/tests && backend/.venv/bin/ruff check backend
    ============================== 66 passed in 1.50s ==============================
    All checks passed!
    ```
