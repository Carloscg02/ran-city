# Plan Técnico: Spec 001 (`001-rf-core-and-antenna-38901`)

## 1. Architecture Alignment
- **Capas afectadas**: Exclusivamente el núcleo puro de dominio y cálculo científico en `backend/ran_city/{domain,antenna,radio}` y su suite de verificación en `backend/tests/`.
- **Aislamiento Hexagonal**: Cero acoplamiento a HTTP (`FastAPI`), ficheros GIS externos o interfaz gráfica. Todo módulo expone funciones puras y modelos inmutables (`Pydantic` / `dataclass(frozen=True)`) operando sobre arrays `NumPy` en `EPSG:25830` (metros).

## 2. ADR Gate & UI Gate
- **ADR Gate**: Alineado con [ADR 0001](../../docs/brain/decisions/0001-initial-architecture.md) (Hexagonal), [ADR 0002](../../docs/brain/decisions/0002-rf-domain-and-map-guardrails.md) (escudo de tipos RF, `EPSG:25830`) y [ADR 0003](../../docs/brain/decisions/0003-tr38901-propagation-matrix.md) (matrices desacopladas `3GPP TR 38.901` sobre `ScenarioGrid` `5m/12m/50m`).
- **UI / Frontend Gate**: No aplica en `Spec 001` (sin componentes visuales; `docs/brain/design.md` y Playwright E2E permanecen diferidos hasta la primera spec con frontend).

## 3. Diseño de Módulos y Contratos de Seams Públicos

```text
backend/
├── pyproject.toml
├── ran_city/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── units.py       # Seam 1a: Dbm, Db, LinearMw, AzimuthDeg, ZenithDeg, Point3D
│   │   ├── grid.py        # Seam 1b: EnvironmentType (5/12/50m), ScenarioGrid, GridGeometry
│   │   └── models.py      # Seam 2: DataSourceOrigin, CellType, NrBand, AntennaConfig, Cell, Sector, Site
│   ├── antenna/
│   │   ├── __init__.py
│   │   └── tr38901.py     # Seam 3: gcs_to_lcs_angles, element_gain_dbi, panel_gain_dbi, compute_antenna_gain_matrix
│   └── radio/
│       ├── __init__.py
│       ├── tr38901.py     # Seam 4: CalibrationParams, PropagationMatrix, los_probability, sample_los_mask, compute_propagation_matrix
│       └── coverage.py    # Seam 5: CellCoverageResult, ScenarioCoverageResult, power_per_re_dbm, compute_cell_coverage, compute_scenario_coverage
└── tests/
    ├── test_units_and_grid.py
    ├── test_domain_models.py
    ├── test_antenna_tr38901.py
    ├── test_propagation_tr38901.py
    └── test_coverage_matrices.py
```

### Detalle Técnico por Seam
1. **Seam 1 (`units.py` + `grid.py`)**:
   - `Dbm`, `Db`, `LinearMw`: constructores con conversión explícita (`to_mw()`, `from_mw()`, suma permitida en `LinearMw` y bloqueada entre dos `Dbm` para impedir errores físicos).
   - `AzimuthDeg` (normaliza a `[0, 360)`), `ZenithDeg` (valida `[0, 180]`), `Point3D(x_m, y_m, z_m)`.
   - `EnvironmentType`: `DENSE_URBAN` (`5.0 m`), `URBAN` (`12.0 m`), `RURAL` (`50.0 m`).
   - `ScenarioGrid.from_bounds(x_min, y_min, x_max, y_max, environment, ground_z_m=0.0, rx_height_m=1.5)`: genera mallas regulares 2D de centros de píxel (`shape = (n_y, n_x)`) y método `geometry_from_tx(tx_pos: Point3D) -> GridGeometry` con arrays 2D `d2d_m`, `d3d_m` ($\ge 1.0\text{ m}$), `zenith_gcs_deg` y `azimuth_gcs_deg` (`atan2(dx, dy) % 360`).
2. **Seam 2 (`models.py`)**:
   - Modelos `Pydantic` (`ConfigDict(frozen=True)`) validando invariantes físicos: $0.5 \le f_{c,\text{GHz}} \le 100.0$, $N_V, N_H \ge 1$, $N_{\text{RB}} \ge 1$, etiqueta obligatoria `source: DataSourceOrigin` y presets `NrBand.n28()`, `NrBand.n78()`, `NrBand.n258()`.
3. **Seam 3 (`antenna/tr38901.py`)**:
   - Operaciones 100% vectorizadas en `NumPy` (aceptan escalares `float` o `ndarray` 2D): `gcs_to_lcs_angles`, `element_gain_dbi` (`Table 7.3-1`), `panel_gain_dbi` (`UPA` $N_V \times N_H$ con pesos normalizados $1/\sqrt{N_V N_H}$) y `compute_antenna_gain_matrix(antenna, sector_azimuth, grid_geom)`.
4. **Seam 4 (`radio/tr38901.py`)**:
   - `los_probability(d2d_m, cell_type, h_ut_m)` (`Table 7.4.2-1`), `sample_los_mask(prob_los, seed)` y `compute_propagation_matrix(cell_type, freq_ghz, h_bs_m, h_ut_m, grid_geom, seed=42, los_mask=None, calibration=CalibrationParams()) -> PropagationMatrix` (`Table 7.4.1-1` `UMa` / `UMi - Street Canyon`).
5. **Seam 5 (`radio/coverage.py`)**:
   - `power_per_re_dbm(tx_power_dbm, num_rbs)` y ensamblaje desacoplado: recibe `PropagationMatrix` precalculada + `Cell` + `Sector` para producir `effective_loss_db` y `rsrp_dbm` en milisegundos al variar tilts, además de `compute_scenario_coverage` (`serving_rsrp_dbm`, `best_server_idx`).

## 4. Estrategia de Ejecución Pedagógica (Modo 2 + `subagent-fast`)
- **Tarea 1 (Andamiaje)**: Delegada directamente al subagente constructor rápido (`flash`) para dejar operativo `backend/.venv`, `pytest`, `hypothesis` y `ruff`.
- **Tareas 2 a 5 (Co-implementación guiada bloque a bloque)**: Se ejecutan secuencialmente con revisión explícita de ecuaciones y resultados observados con el usuario para asegurar comprensión total línea a línea.
