# Módulo Funcional: Motor Matricial de Antenas y Propagación 5G (`rf-antenna-and-propagation-engine`)

> Capacidad vertical que resuelve el mallado métrico por entorno, la radiación directiva 3GPP de paneles de antena y las matrices desacopladas de propagación y cobertura `SS-RSRP`.

## 1. Entidades y Unidades de Dominio (`backend/ran_city/domain/`)
- **`units.py`**: `LinearMw`, `Db`, `Dbm` (bloquea `Dbm + Dbm`), `AzimuthDeg` (`0°=Norte` horario), `ZenithDeg` (`90°=horizonte` 3GPP), `Point3D` (`EPSG:25830`).
- **`grid.py`**: `EnvironmentType` (`DENSE_URBAN=5 m`, `URBAN=12 m`, `RURAL=50 m`), `ScenarioGrid` y tensor geométrico `GridGeometry` (`d2d_m`, `d3d_m`, `zenith_gcs_deg`, `azimuth_gcs_deg`).
- **`models.py`**: `Site -> Sector -> Cell -> AntennaConfig` y `NrBand` (`n28`, `n78`, `n258` según 3GPP TS 38.104), `CellType` (`macro`, `micro`, `pico`) y trazabilidad `DataSourceOrigin` (`real`, `estimated`, `synthetic`).

## 2. Motores de Cálculo y Seams Públicos
- **Antena (`backend/ran_city/antenna/tr38901.py`)**:
  - `gcs_to_lcs_angles` (rotación mecánica `GCS -> LCS`, TR 38.901 Clause 7.1.3).
  - `element_gain_dbi` (patrón 3D Table 7.3-1).
  - `panel_gain_dbi` y `compute_antenna_gain_matrix` (array plano `UPA` con kernel cerrado de Dirichlet y tilt/scan eléctrico, ITU-R M.2101-0).
- **Propagación (`backend/ran_city/radio/tr38901.py`)**:
  - `los_probability` y `sample_los_mask` (TR 38.901 Table 7.4.2-1 con semilla reproducible o `los_mask` geométrica inyectada).
  - `compute_propagation_matrix` (`UMa` para `macro`, `UMi - Street Canyon` para `micro`/`pico`, Table 7.4.1-1) y `CalibrationParams` para futuro ajuste con *Drive Test*.
- **Cobertura (`backend/ran_city/radio/coverage.py`)**:
  - `power_per_re_dbm` (TS 38.215 / TS 38.211), `compute_cell_coverage` (desacopla `L_prop` de `G_ant`) y `compute_scenario_coverage` (`serving_rsrp_dbm` y `best_server_idx`).

## 3. Adaptadores Conectados
- Actualmente consumido de forma pura en memoria (`Spec 001`); en `Spec 002+` se conectará a la ingesta GIS de Jaén (`data_sources`, `geo`) y al adaptador HTTP `FastAPI` + rasters `PNG` para `MapLibre`/`deck.gl`.

## 4. Suite de Verificación (`38 tests`)
- `backend/tests/test_units_and_grid.py`
- `backend/tests/test_domain_models.py`
- `backend/tests/test_antenna_tr38901.py`
- `backend/tests/test_propagation_tr38901.py`
- `backend/tests/test_coverage_matrices.py`
