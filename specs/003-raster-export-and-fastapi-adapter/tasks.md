# Tareas de Implementación: Spec 003 (`003-raster-export-and-fastapi-adapter`)

> Flujo SDD en 6 pasos: Implementación TDD por `Builder Subagent` (`flash`) + `Independent Audit Gate` por `Auditor Subagent` (estrictamente read-only). Toda tarea completada `[x]` debe registrar su bloque de `Prueba Observada:` real.

- [x] Tarea 1: Dependencias (`fastapi`, `uvicorn`, `pillow`) y Seam 1 — Codificador ráster `NumPy -> PNG RGBA` con inversión Norte-Sur y *Bounding Box* WGS84 (`ran_city.geo.raster`).
  - Añadir `fastapi>=0.110`, `uvicorn>=0.29` y `pillow>=10.3` en `backend/pyproject.toml` e instalar en `backend/.venv`.
  - Ciclo `RED -> GREEN -> REFACTOR` en `test_raster_and_whatif.py` y `geo/raster.py` verificando dimensiones `(width=n_x, height=n_y)`, orientación Norte en fila `0` del `PNG`, transparencia `alpha=0` en `NaN`s / bajo umbral, y `bounds_wgs84` válidos en `EPSG:4326`.
  - **Prueba Observada**:
    ```bash
    $ backend/.venv/bin/pytest backend/tests/test_raster_and_whatif.py -k "TestRasterExportSeam1"
    collected 8 items / 3 deselected / 5 selected
    backend/tests/test_raster_and_whatif.py ..... [100%]
    5 passed, 3 deselected in 0.35s
    ```

- [x] Tarea 2: Seam 2 — Motor inmutable de experimentos *What-If* (`ran_city.radio.whatif`).
  - Ciclo `RED -> GREEN -> REFACTOR` en `test_raster_and_whatif.py` y `radio/whatif.py` verificando `CellOverride` (tilts mecánico/eléctrico, potencia TX, estado `active`) y `SectorOverride` (`azimuth_deg`, `ant_height_m`), inmutabilidad de los objetos `Site` originales y `ValueError` ante IDs inexistentes.
  - **Prueba Observada**:
    ```bash
    $ backend/.venv/bin/pytest backend/tests/test_raster_and_whatif.py -k "TestWhatIfSeam2"
    collected 8 items / 5 deselected / 3 selected
    backend/tests/test_raster_and_whatif.py ... [100%]
    3 passed (including hypothesis property tests), 5 deselected in 0.52s
    ```

- [x] Tarea 3: Seam 3 — Adaptador HTTP `FastAPI` (`ran_city.api`) para escenario Jaén, cobertura ráster *What-If*, inspector puntual de *Link Budget* y cortes polares de antena.
  - Ciclo `RED -> GREEN -> REFACTOR` en `test_api_endpoints.py`, `api/schemas.py` y `api/app.py` verificando con `TestClient` los endpoints `GET /api/health`, `GET /api/cities/jaen`, `POST /api/cities/jaen/coverage`, `POST /api/cities/jaen/inspect-point` y `POST /api/antenna/pattern`.
  - **Prueba Observada**:
    ```bash
    $ backend/.venv/bin/pytest backend/tests/test_api_endpoints.py
    collected 5 items
    backend/tests/test_api_endpoints.py ..... [100%]
    5 passed in 0.95s

    $ backend/.venv/bin/pytest backend/tests
    79 passed, 1 warning in 2.25s

    $ backend/.venv/bin/ruff check backend
    All checks passed!

    $ compass check
    === COMPASS_CHECK_PASSED ===
    Tareas con Prueba Observada auditadas: 13 completadas validas
    ```
