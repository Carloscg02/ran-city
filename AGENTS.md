# AGENTS.md - Router y Politicas de Agente para `RAN-city`

> Enrutador principal de contexto. Lee este archivo al inicio de cada sesion.

---

## 1. Memoria Central del Proyecto
- Consulta siempre [`docs/brain/index.md`](docs/brain/index.md) para el mapa de arquitectura y estado vivo.
- Consulta [`docs/brain/handoff.md`](docs/brain/handoff.md) para retomar el trabajo donde se quedo.

---

## 2. Decisor de Carriles de Ejecucion
- Carril 1: `ANSWER` - Preguntas de orientacion, explicaciones y diseno conceptual sin edicion de ficheros.
- Carril 2: `FTD` (Fix-The-Docs) - Correcciones directas en documentacion, arquitectura o handoff sin codigo de produccion.
- Carril 3: `SDD` (Spec-Driven Development) - Flujo formal en 6 pasos: `spec.md` -> `plan.md` -> `tasks.md` -> `TDD Implementation` (Builder) -> `Independent Audit Gate` (Auditor read-only: `APPROVED` | `REQUEST_CHANGES`) -> `Brain Consolidation & Guide` (Main).

---

## 3. Estrategia de Modelos y Delegacion
- Delegacion en Subagentes Ligeros (`subagent-fast`) - Triada de roles:
  1. Main Agent (Orquestador / Arquitecto / Mentor): Contexto principal y coordinacion.
  2. Builder Subagent (Constructor TDD): Modelo rapido (`flash` / fast tier) para el ciclo RED-GREEN-REFACTOR.
  3. Auditor Subagent (Auditor Adversarial): Estrictamente read-only (`flash` por defecto, `pro` bajo demanda). Reporte por severidad y veredicto formal (`APPROVED` | `REQUEST_CHANGES`).

---

## 4. Catalogo de Skills Instaladas
- [project-architect](.compass/skills/project-architect/SKILL.md): Negociacion de arquitectura y diagnostico de proyecto.
- [sdd-workflow](.compass/skills/sdd-workflow/SKILL.md): Flujo formal de especificacion, Seams y verificacion proporcional.
- [tdd](.compass/skills/tdd/SKILL.md): Ciclo estricto red-green-refactor y testing en seams publicos.
- [mentor-guide](.compass/skills/mentor-guide/SKILL.md): Generacion de guias educativas bajo demanda.
- [ui-design](.compass/skills/ui-design/SKILL.md): Gobernanza de diseno UI/Frontend, entrevista guiada y reglas Anti-Slop.

---

## 5. UI / Frontend Gate (Just-In-Time Design & Agent Eyes)
- Cuando una tarea (`FTD` o `SDD`) vaya a crear o modificar interfaz visual (HTML, CSS, Tailwind, React, Vue, Svelte), detenerse antes de escribir codigo: abrir `.compass/skills/ui-design/SKILL.md`, verificar o consensuar `docs/brain/design.md` y asegurar que el agente tiene configurada la verificacion semantica de DOM / navegador (`Agent Eyes`, cambiando `e2e_command` en `docs/brain/architecture.md` si sigue en `N/A`).

---

## 6. Pacto Pedagogico y Rigor de Dominio 5G
- **Cero Cajas Negras en Dominio**: Antes de escribir ecuaciones o maquinas de estado 5G (`radio`, `antenna`, `air_interface`, `protocols`, `mobility`, `kpis`), explicar el concepto fisico/protocolar, citar la fuente publica exacta (3GPP / ITU-R / libro) y dejar que el usuario lo implemente o valide linea a linea (ver `docs/brain/architecture.md`).
- **Apuntes de Asignatura (`docs/course-notes/`)**: Si existen documentos activos en `docs/course-notes/` para el area bajo diseno, tratarlos como requisito normativo antes de cerrar cualquier `spec.md`.
- **Seguimiento Curricular**: Al completar un modulo, actualizar [`docs/SYLLABUS_MAP.md`](docs/SYLLABUS_MAP.md), generar guia didactica en `guides/<slug>-GUIDE.md` (`mentor-guide`) bajo demanda y plantear preguntas cualitativas de comprobacion.
