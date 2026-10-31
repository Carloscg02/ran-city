# Tareas de Implementación: Spec 001 (`001-rf-core-and-antenna-38901`)

> Ciclo estricto `RED -> GREEN -> REFACTOR` en Modo 2 (Co-implementación guiada). Toda tarea completada `[x]` debe registrar su bloque de `Prueba Observada:` real.

- [x] Tarea 1: Andamiaje Python `backend/`, entorno `.venv` (`numpy`, `pydantic`, `pytest`, `hypothesis`, `ruff`) y smoke test inicial.
  - Prueba Observada: pyproject.toml y estructura de paquetes backend/ran_city/{domain,antenna,radio} creados. backend/.venv creado e instalado con pip install -e 'backend[dev]'. pytest backend/tests y ruff check backend ejecutados exitosamente con salida 0 (1 passed in 0.37s).
  - Crear `backend/pyproject.toml` y estructura de paquetes vacíos `backend/ran_city/{domain,antenna,radio}` y `backend/tests/`.
  - Crear `backend/.venv`, instalar paquete editable + dependencias dev y verificar los dos comandos oficiales de `docs/brain/architecture.md`.

- [x] Tarea 2: Seam 1 y Seam 2 — Escudo de unidades RF, `ScenarioGrid` (`5m / 12m / 50m` en `EPSG:25830`) y modelos `Pydantic` (`Site`, `Sector`, `Cell`, `NrBand`).
  - Prueba Observada: pytest backend/tests ejecutó 15 tests pasando en verde en 0.31s (incluyendo 10 tests de unidades RF, conversiones Dbm<->LinearMw, bloqueo Dbm+Dbm, resoluciones ScenarioGrid 5m/12m/50m, orientaciones cardinales y property tests con hypothesis, y 4 tests de modelos Pydantic Site/Sector/Cell/NrBand). ruff check backend verificado con 0 errores.
  - Ciclo `RED -> GREEN` para `units.py` (`Dbm` ↔ `LinearMw`, bloqueo de suma directa en `dBm`, `AzimuthDeg`, `ZenithDeg`), `grid.py` (`EnvironmentType`, `ScenarioGrid`, tensores `d2d_m`, `d3d_m`, `zenith_gcs_deg`, `azimuth_gcs_deg` con propiedades `hypothesis`) y `models.py` (validaciones de bandas NR y topología celular).

- [x] Tarea 3: Seam 3 — Motor vectorizado de Antena `3GPP TR 38.901` (elemento, rotación `GCS -> LCS` por tilt mecánico y array plano `UPA` con tilt eléctrico).
  - Prueba Observada: pytest backend/tests ejecutó 24 tests pasando en verde en 0.39s (9 tests nuevos en test_antenna_tr38901.py validando valores exactos de Table 7.3-1, 8.0 dBi boresight, 5.0 dBi en ±32.5°, saturación -22.0 dBi, pico de array 8x8 en 26.0618 dBi, contraste físico de tilt mecánico sin pérdidas vs tilt eléctrico con scan loss 0.28402 dB dando 25.7778 dBi, cálculo matricial sobre ScenarioGrid sin NaNs ni infs, y cotas e invariantes con hypothesis). ruff check backend verificado con 0 errores.
  - Ciclo `RED -> GREEN` para `antenna/tr38901.py` verificando puntos exactos de `Table 7.3-1` (`8 dBi`, `-3 dB` en `±32.5°`, saturación `30 dB`), ganancia `+10·log10(N_V·N_H)`, contraste físico lateral entre tilt mecánico y eléctrico, y cotas con `hypothesis`.

- [x] Tarea 4: Seam 4 — Probabilidad `LOS` (`Table 7.4.2-1`) y Matriz de Propagación `3GPP TR 38.901` (`UMa` / `UMi - Street Canyon`, `Table 7.4.1-1`) con `CalibrationParams`.
  - Prueba Observada: pytest backend/tests ejecutó 34 tests pasando en verde en 0.54s (10 tests en test_propagation_tr38901.py verificando Pr_LOS exacto <=18m y decaimiento analítico a 100m, reproducibilidad con seed y los_mask explícita, path loss UMa y UMi antes y después del breakpoint d'_BP, condición PL_NLOS >= PL_LOS, calibración +3.5 dB y monotonía con hypothesis). ruff check backend verificado con 0 errores.
  - Ciclo `RED -> GREEN` para `radio/tr38901.py` validando `Pr_LOS` (`<= 18 m` y caída exponencial), máscara reproducible por `seed` e inyección `los_mask`, ramas `PL_1`/`PL_2` alrededor de `d'_BP`, condición `PL_NLOS >= PL_LOS`, aplicación de `CalibrationParams` e invariantes `hypothesis`.

- [x] Tarea 5: Seam 5 — Matrices de Cobertura Desacopladas (`P_TX,RE`, `L_eff`, `RSRP`, `Best Server` trisectorial) e invariancia rotacional extremo a extremo.
  - Prueba Observada: pytest backend/tests ejecutó 38 tests pasando en verde en 0.62s (4 tests en test_coverage_matrices.py validando potencia por RE de 7.84656 dBm, desacoplo de matriz de propagación intacta al variar tilts, partición celular trisectorial 0°/120°/240° con best_server_idx coherente, e invariancia rotacional horaria idéntica en RSRP con hypothesis). ruff check backend verificado con 0 errores.
  - Ciclo `RED -> GREEN` para `radio/coverage.py` comprobando que cambiar tilts recalcula `G_ant` y `RSRP` sin mutar `L_prop`, partición espacial coherente en un sitio trisectorial (`0°/120°/240°`) e invariancia rotacional con `hypothesis`.
