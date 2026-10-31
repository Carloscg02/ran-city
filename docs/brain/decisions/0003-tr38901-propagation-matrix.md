# ADR 0003: Adopcion de 3GPP TR 38.901 sobre Matrices Desacopladas por Zona

- **Estado**: Aceptado
- **Fecha**: 2026-10-31
- **Decisiones Relacionadas**: [ADR 0001](0001-initial-architecture.md), [ADR 0002](0002-rf-domain-and-map-guardrails.md)

## 1. Contexto
Los requisitos academicos de planificacion celular (`docs/course-notes/001_propagacion_mallado_T2.md`) exigen evitar `FSPL` como calculo final de cobertura, evaluar matrices de propagacion sobre mallas por entorno (`5 m` Denso, `12 m` Urbano, `50 m` Rural), contemplar tipos `macro`/`micro`/`pico` y tilts mecanico/electrico, y permitir calibracion futura con *Drive Test*. Aunque dichos apuntes citan COST 231 Walfisch-Ikegami como ejemplo clasico, su validez empirica (`800-2000 MHz`, `d >= 20 m`) entra en conflicto con las bandas clave de 5G NR (`n28 = 700 MHz`, `n78 = 3.5 GHz`, `n258 = 26 GHz`) y con el mallado denso de `5 m`.

## 2. Decision
1. Adoptar **3GPP TR 38.901 (`UMa` para `macro`, `UMi - Street Canyon` para `micro`/`pico`)** como modelo semideterminista base nativo para `0.5-100 GHz`.
2. Evaluar la condicion `LOS/NLOS` sobre cada pixel de `ScenarioGrid` mediante la probabilidad `LOS` de **TR 38.901 Table 7.4.2-1** (con semilla reproducible), permitiendo inyectar una mascara geometrica explicita `los_mask` cuando se incorporen los edificios reales del Catastro.
3. Desacoplar el calculo por celda en dos matrices `(N_y, N_x)`: **Matriz de Propagacion Isotropa (`L_prop`)** (cacheable e independiente del tilt, con `CalibrationParams` aditivos/logaritmicos para *Drive Test*) y **Matriz Directiva de Antena (`G_ant`)** (donde actuan el azimut y los tilts mecanico y electrico).

## 3. Consecuencias
- Cumplimiento simultaneo del rigor academico de planificacion celular y de las especificaciones 5G NR 3GPP.
- Recalculo en milisegundos al ajustar tilts o potencias en el *Sandbox What-If* sin repetir el modelo de propagacion.
