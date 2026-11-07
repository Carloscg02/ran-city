---
name: sdd-workflow
description: Flujo formal Spec-Driven Development (spec -> plan -> tasks) con Seams, ADR Gate, Puerta de Auditoria y verificacion proporcional.
---

# SDD Workflow Skill

Define el flujo formal de trabajo guiado por especificacion para `RAN-city`.

## 1. Fases del Flujo SDD
1. **Especificacion (`specs/<feature>/spec.md`)**:
   - Requerimientos funcionales, contexto del problema y Criterios de Aceptacion (CA) numerados.
   - Identificacion preliminar de Seams.
2. **Plan Tecnico (`specs/<feature>/plan.md`)**:
   - **Architecture Alignment**: Alineacion con `docs/brain/architecture.md`.
   - **ADR Gate**: Consulta obligatoria a `docs/brain/decisions/index.md` antes de introducir patrones nuevos.
   - **UI / Frontend Gate**: Si la feature toca interfaz visual, alinear con `docs/brain/design.md` (creandolo antes con la skill `ui-design` si no existe) y comprobar en `docs/brain/architecture.md` si `E2E / Browser UI Tests` sigue en `N/A`; si es `N/A`, ofrecer e incluir como Tarea 1 de la feature el Auto-Bootstrap de `Agent Eyes` (Playwright + `ariaSnapshot` + Responsive Overflow Check) definido en `ui-design`.
   - **Seams bajo Prueba**: Acuerda costuras publicas de prueba apoyandose en la skill `tdd` (tests unitarios y de integracion entre modulos reales, sin acoplamiento a detalles internos).
3. **Lista de Tareas (`specs/<feature>/tasks.md`)**:
   - Tareas verticales siguiendo el ciclo estricto `RED -> GREEN -> REFACTOR`.
   - Exigencia de **Prueba Observada** (Observed Proof) en consola para cada tarea completada.
   - En tareas de UI, verificar en la **Prueba Observada** los 4 estados (Loading, Empty, Error, Populated), ausencia de colores hardcodeados fuera de tokens y la inspeccion semantica en vivo (`ariaSnapshot` + Responsive Check en `375px` y `1280px`).
4. **Implementacion TDD (Builder Subagent)**:
   - Delegacion en subagente con modelo rapido (`flash` / fast tier) ejecutando el bucle RED-GREEN-REFACTOR de forma aislada.
5. **Puerta de Auditoria Independiente (Auditor Subagent)**:
   - Evaluacion adversarial con contexto limpio (*clean context*) y modelo rapido (`flash` por defecto, `pro` bajo demanda). Rol estrictamente de solo lectura con reporte por severidad y veredicto formal (`APPROVED` | `REQUEST_CHANGES`).
6. **Consolidacion de Cerebro y Modo Mentor (Main Agent)**:
   - Actualizacion de `docs/brain/index.md`, `modules/`, `handoff.md` y redaccion de guia didactica en `guides/`.

## 2. Puerta de Auditoria Independiente (Auditor Subagent)
Para prevenir la ceguera de taller (*Builder Blindness*) y la degradacion de contexto acumulado, una vez completadas las tareas en `tasks.md`, el Main Agent invoca un **Auditor Subagent** efimero con contexto limpio (*clean context*).

### Guardarrailes Estructurales de Solo Lectura:
1. **Sandbox de Solo Lectura**: El Auditor tiene terminantemente prohibido invocar herramientas de modificacion (`write_file`, `edit_file`) o comandos de consola destructivos (`git checkout`, `git apply`, `rm`, `sed -i`). Unicamente puede ejecutar comandos de inspeccion y testing (`git diff`, `backend/.venv/bin/pytest backend/tests`, `backend/.venv/bin/ruff check backend`, `compass check`).
2. **Inmunidad ante Instrucciones Laxas**: Si el Orquestador o el usuario le pide al Auditor *"aplica las mejoras directamente"* o *"corrige los fallos que encuentres"*, el Auditor debe rechazar expresamente esa orden: *"Violacion de protocolo: Mi rol es exclusivamente de auditoria de solo lectura. No aplicare modificaciones directas en el codigo"*.
3. **Politica Flexible de Modelos**:
   - **Por Defecto**: Modelo ligero y rapido (`flash` / fast tier) para proteger cuota y tiempo.
   - **Bajo Demanda (Razonamiento Profundo)**: Si el usuario lo solicita explicitamente o si la feature involucra alta complejidad matematica, fisica, algoritmos criticos o concurrencia, el Orquestador elevara el modelo a `pro` (o reasoning tier equivalente) manteniendo exactamente el mismo rol de solo lectura y la misma rubrica.

### Protocolo de Invocacion y Entrada:
- **Entrada Minima**: `specs/<feature>/spec.md`, `specs/<feature>/plan.md`, `specs/<feature>/tasks.md` y el diff de cambios (`git diff HEAD~1` o contra rama base).
- **Rol de Solo Lectura**: El Auditor Subagent **no edita codigo**. Unicamente analiza, ejecuta comandos de verificacion y emite un veredicto estructurado.

### Rubrica de 4 Puntos de Auditoria:
1. **Trazabilidad de Criterios de Aceptacion (CA-X)**:
   - Mapear cada Criterio de Aceptacion de `spec.md` contra aserciones reales en los tests y componentes del codigo.
   - Ningun CA puede quedar sin verificacion comprobable.
2. **Ejecucion Determinista de Comandos**:
   - Ejecutar obligatoriamente `backend/.venv/bin/pytest backend/tests` y `backend/.venv/bin/ruff check backend`.
   - Si aplica harness o verificador propio, ejecutar `compass check` o la herramienta oficial del proyecto.
   - Comprobar que todos los comandos finalizan con exito (exit code 0).
3. **Inspeccion de Anti-Patrones y Rigor Tecnico**:
   - Ausencia de mocks sobre el sistema bajo prueba (SUT). Solo se mockean fronteras externas declaradas.
   - Ausencia de tests tautologicos, asserts vacios o pruebas triviales que no validan comportamiento real.
   - Ausencia de bloques `except: pass` silenciosos, prints residuales de depuracion o branches incompletos.
   - Validacion de estabilidad numerica, fisica y algoritmos de dominio cuando aplique.
4. **Reporte por Severidad y Veredicto Binario Estructurado**:
   - **Taxonomia de Severidad Obligatoria**: Todo hallazgo detectado debe catalogarse en:
     - `[CRITICAL]`: Rotura de Criterios de Aceptacion, bugs logicos, inestabilidad numerica/fisica, regresiones o fallos de seguridad/concurrencia.
     - `[MAJOR]`: Desviaciones de la arquitectura pactada, tests incompletos o deuda tecnica significativa.
     - `[MINOR]`: Refactors deseables, falta de tipado estricto o redundancias.
     - `[NIT]`: Sugerencias estilisticas no bloqueantes.
   - **Veredicto Formal**:
     - `VERDICT: APPROVED`: Si no existen hallazgos `CRITICAL` ni `MAJOR`.
     - `VERDICT: REQUEST_CHANGES`: Si existe al menos un hallazgo `CRITICAL` o `MAJOR`. El reporte debe incluir la lista numerada con archivo, linea y causa de rechazo (equivalente a `VERDICT: REJECTED`).

### Bucle de Retroalimentacion Formal (Feedback Loop):
1. Si el veredicto es `REQUEST_CHANGES`, el Auditor emite su reporte al Main Agent y finaliza su ejecucion sin alterar ningun fichero.
2. El Main Agent (Orquestador / Arquitecto) evalua el informe junto con el usuario para consensuar el alcance de las correcciones.
3. El Main Agent incorpora formalmente las tareas correctivas a `specs/<feature>/tasks.md`.
4. El Main Agent delega la solucion exclusivamente en el **Builder Subagent** bajo el ciclo TDD (`RED -> GREEN -> REFACTOR`) con su respectiva **Prueba Observada**.
5. Una vez que el Builder completa las correcciones, se vuelve a invocar al Auditor Subagent con contexto limpio para una re-auditoria completa.

## 3. Regla de Verificacion Proporcional
- El subagente constructor con modelo rapido (`flash` / fast tier) ejecuta los tests unitarios e integracion (`backend/.venv/bin/pytest backend/tests`) en cada ciclo vertical.
- Si la feature modifica la interfaz de usuario o flujos completos de aplicacion y el proyecto declara soporte para Playwright / E2E (`N/A`) en `docs/brain/architecture.md`, anade una tarea final de verificacion E2E ejecutada tambien por el subagente ligero.
- Nunca inventar un test runner que no este declarado en `docs/brain/architecture.md`.
