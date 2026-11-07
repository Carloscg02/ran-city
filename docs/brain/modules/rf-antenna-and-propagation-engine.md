# Módulo Funcional: Motor Matricial de Antenas, Propagación y Link Budget 5G (`rf-antenna-and-propagation-engine`)

> Capacidad vertical que resuelve el mallado métrico por entorno (con soporte para relieve 3D `MDT05`), la radiación directiva 3GPP de paneles de antena y las matrices desacopladas de propagación (`UMa`/`UMi`), *Shadow Fading* 2D correlado, cobertura `SS-RSRP`, ruido térmico por `RE` y `SINR` co-canal en `mW`.

## 1. Entidades y Unidades de Dominio (`backend/ran_city/domain/`)
- **`units.py`**: `LinearMw`, `Db`, `Dbm` (bloquea `Dbm + Dbm`), `AzimuthDeg` (`0°=Norte` horario), `ZenithDeg` (`90°=horizonte` 3GPP), `Point3D` (`EPSG:25830`).
- **`grid.py`**: `EnvironmentType` (`DENSE_URBAN=5 m`, `URBAN=12 m`, `RURAL=50 m`), `ScenarioGrid` (con soporte de matriz topográfica `terrain_z_m` vía `with_terrain()`) y tensor geométrico `GridGeometry` (`d2d_m`, `d3d_m`, `zenith_gcs_deg`, `azimuth_gcs_deg`).
- **`models.py`**: `Site -> Sector -> Cell -> AntennaConfig` y `NrBand` (`n28`, `n78`, `n258` según 3GPP TS 38.104), `CellType` (`macro`, `micro`, `pico`) y trazabilidad `DataSourceOrigin` (`real`, `estimated`, `synthetic`).

## 2. Motores de Cálculo y Seams Públicos
- **Antena (`backend/ran_city/antenna/tr38901.py`)**:
  - `gcs_to_lcs_angles` (rotación mecánica `GCS -> LCS`, TR 38.901 Clause 7.1.3).
  - `element_gain_dbi` (patrón 3D Table 7.3-1).
  - `panel_gain_dbi` y `compute_antenna_gain_matrix` (array plano `UPA` con kernel cerrado de Dirichlet y tilt/scan eléctrico, ITU-R M.2101-0).
- **Propagación y *Shadow Fading* (`backend/ran_city/radio/tr38901.py`)**:
  - `los_probability` y `sample_los_mask` (TR 38.901 Table 7.4.2-1 con semilla reproducible o `los_mask` geométrica inyectada).
  - `shadow_fading_std_db` (Table 7.4.1-1), `decorrelation_distance_m` (Table 7.5-6) y `sample_shadow_fading_map` (filtrado gaussiano 2D con renormalización exacta de varianza unitaria incluso en bordes).
  - `compute_propagation_matrix` (`UMa` para `macro`, `UMi - Street Canyon` para `micro`/`pico`, Table 7.4.1-1, `include_shadow_fading`) y `CalibrationParams` para ajuste con *Drive Test*.
- **Cobertura, Ruido Térmico y `SINR` (`backend/ran_city/radio/coverage.py`)**:
  - `power_per_re_dbm` (TS 38.215 / TS 38.211), `thermal_noise_dbm` y `re_thermal_noise_dbm` ($k_B T_0 B F$ con $k_B = 1.380649 \times 10^{-23}\text{ J/K}$, TS 38.101-1 Clause 7.3).
  - `compute_cell_coverage` (desacopla `L_prop` de `G_ant`) y `compute_scenario_coverage` (`serving_rsrp_dbm`, `best_server_idx`, `noise_per_re_dbm`, `interference_mw` y `sinr_db` con aislamiento por `network_alias` y `n_band`).

## 3. Suite de Verificación
- `backend/tests/test_units_and_grid.py`
- `backend/tests/test_domain_models.py`
- `backend/tests/test_antenna_tr38901.py`
- `backend/tests/test_propagation_tr38901.py`
- `backend/tests/test_coverage_matrices.py`
