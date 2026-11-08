# Handoff del Proyecto: `RAN-city`

- **Estado Actual en `main`**: `Spec 002` completada, testeada (`66 passed`, `0` errores `ruff`) y sincronizada con `compass update`.
- **Rama Experimental Disponible (`feat/spec-003-backend-api`)**:
  - Contiene ya implementada y auditada (`79 passed`) la parte backend no-UI (`ran_city.geo.raster` PNG RGBA, `ran_city.radio.whatif` y endpoints `FastAPI` en `ran_city.api`).
  - **Dos caminos posibles al abrir sesión con Claude Opus 5.5**:
    1. **Usar el backend pre-construido (Ahorro de cuota)**: Hacer `git checkout feat/spec-003-backend-api` y abordar directamente la **`Spec 004`** dedicada 100% al **UI / Frontend Gate** (`docs/brain/design.md`) y al frontend `React + MapLibre GL + deck.gl`. Si el resultado final convence, hacer merge a `main`.
    2. **Empezar limpio desde `main`**: Permanecer en `main` y ejecutar la **`Spec 003` completa** (UI Gate + Backend FastAPI + Frontend MapLibre/deck.gl) íntegramente con Claude Opus 5.5.
- **Activación Obligatoria del UI / Frontend Gate en ambos casos**:
  1. Abrir [`.compass/skills/ui-design/SKILL.md`](../../.compass/skills/ui-design/SKILL.md) y consensuar [`docs/brain/design.md`](design.md) antes de escribir código visual.
  2. Configurar *Agent Eyes* en `frontend/` (Playwright + `ariaSnapshot` + responsive `375px/1280px`) y actualizar `e2e_command` en [`docs/brain/architecture.md`](architecture.md).
- **Bloqueos Activos**: Ninguno.
