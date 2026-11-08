# Handoff del Proyecto: `RAN-city`

- **Estado Actual**: `Spec 001`, `Spec 002` y `Spec 003` completadas, auditadas (`VERDICT: APPROVED`) y verificadas (`79 passed` en `pytest`, `0` errores en `ruff`, `COMPASS_CHECK_PASSED`).
- **Ultima Tarea**: Implementado en `Spec 003` todo el backend no-UI que alimentará al frontend: codificador ráster `NumPy -> PNG RGBA` con inversión Norte-Sur (`ran_city.geo.raster`), motor inmutable *What-If* (`ran_city.radio.whatif`) y API `FastAPI` completa en `EPSG:4326` (`GET /api/cities/jaen`, `POST /api/cities/jaen/coverage`, `POST /api/cities/jaen/inspect-point`, `POST /api/antenna/pattern`).
- **Siguiente Paso (Nuevo Chat con Claude Opus 5.5 — 100% Diseño Visual y UI)**:
  - Arrancar **`Spec 004` (`004-jaen-map-ui-and-whatif-sandbox`)** dedicada exclusivamente a la dirección estética y al frontend `React + TypeScript + Vite + Tailwind + MapLibre GL JS + @deck.gl/maplibre`.
  - **Paso 1 (UI / Frontend Gate)**: Abrir [`.compass/skills/ui-design/SKILL.md`](../../.compass/skills/ui-design/SKILL.md), realizar la entrevista guiada con el usuario y crear [`docs/brain/design.md`](design.md) (arquetipo estético, tokens semánticos, tipografía con `tabular-nums`, 4 estados obligatorios y reglas Anti-Slop).
  - **Paso 2 (Frontend + Agent Eyes)**: Construir `frontend/` consumiendo los endpoints ya listos de `ran_city.api` (sin tocar código Python 5G) y configurar Playwright `Agent Eyes` (`ariaSnapshot` + chequeo responsive `375px` y `1280px` en `docs/brain/architecture.md`).
- **Bloqueos Activos**: Ninguno.
