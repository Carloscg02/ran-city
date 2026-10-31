---
name: sdd-workflow
description: Flujo formal Spec-Driven Development (spec -> plan -> tasks) con Seams, ADR Gate y verificacion proporcional.
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

## 2. Regla de Verificacion Proporcional
- El subagente constructor con modelo rapido (`flash` / fast tier) ejecuta los tests unitarios e integracion (`backend/.venv/bin/pytest backend/tests`) en cada ciclo vertical.
- Si la feature modifica la interfaz de usuario o flujos completos de aplicacion y el proyecto declara soporte para Playwright / E2E (`N/A`) en `docs/brain/architecture.md`, anade una tarea final de verificacion E2E ejecutada tambien por el subagente ligero.
- Nunca inventar un test runner que no este declarado en `docs/brain/architecture.md`.
