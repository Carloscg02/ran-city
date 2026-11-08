# Handoff del Proyecto: `RAN-city`

- **Estado Actual**: `Spec 002` completada, testeada (`66 passed`, 0 errores `ruff`), sincronizada con `compass update` y subida a remoto (`9905bc1`).
- **Ultima Tarea**: Sincronizado el arnés con `compass update` (auditor de solo lectura, inmunidad a órdenes laxas y política flexible de modelos).
- **Siguiente Paso (Nuevo Chat con Claude Opus 5.5)**:
  - Arrancar **`Spec 003`** (Frontend UI + Adaptador API FastAPI + Rasterizado PNG de Cobertura sobre Jaén).
  - **Activación Obligatoria del UI / Frontend Gate**:
    1. Antes de picar código frontend, ejecutar el protocolo de [`.compass/skills/ui-design/SKILL.md`](../.compass/skills/ui-design/SKILL.md) para consensuar y crear [`docs/brain/design.md`](docs/brain/design.md) (arquetipo estético, tokens semánticos, tipografía con `tabular-nums`, 4 estados obligatorios y reglas anti-slop).
    2. Auto-bootstrap de *Agent Eyes* en `frontend/` (Playwright + `ariaSnapshot` + test responsive `375px/1280px`) y actualizar `e2e_command` en [`docs/brain/architecture.md`](docs/brain/architecture.md).
    3. Construir la UI interactiva (`React + TypeScript + Vite + MapLibre GL JS + @deck.gl/maplibre BitmapLayer`) conectada a los endpoints finos de FastAPI (`/api/cities/jaen`, `/api/coverage/raster`).
- **Bloqueos Activos**: Ninguno. (Las preguntas conceptuales y la guía didáctica de Spec 002 se abordarán cuando el usuario lo indique).
