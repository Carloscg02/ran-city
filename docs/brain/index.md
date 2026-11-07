# Cerebro del Proyecto: `RAN-city`

> Mapa central de contexto del proyecto (Nivel 1). Consulta los documentos de Nivel 2 segun necesidad.

---

## 1. Identidad del Proyecto
- **Nombre**: `RAN-city`
- **Objetivo**: Simulador interactivo y laboratorio educativo de redes 5G RAN sobre Jaen (Zoom de escala: Ciudad -> Antena -> Celda PHY -> UE/Movilidad -> KPIs, con red base estimada OpenCelliD/OSM y sandbox What-If)
- **Stack Tecnologico**: `Python 3 (venv, FastAPI, Pydantic, NumPy/SciPy, GeoPandas, Pytest + Hypothesis) + TypeScript, React, Vite, MapLibre GL, deck.gl`
- **Dominio**: 5G NR Radio Access Network (3GPP Physical Layer, Antenna Systems TR 38.901, RF Propagation, RAN Protocols & PM KPIs)

---

## 2. Documentos Centrales (Nivel 2)
- **[`architecture.md`](architecture.md)** - Diseno de capas, guardarrailes RF/GIS, pacto pedagogico y comandos de verificacion.
- **[`handoff.md`](handoff.md)** - Estado del turno actual y siguiente paso inmediato (maximo 30 lineas).
- **[`decisions/index.md`](decisions/index.md)** - Sub-indice de decisiones tecnicas irreversibles (ADRs). Consultar solo ante decisiones arquitectonicas.
- **[`VISION.md`](../../VISION.md)** - Vision funcional del producto ("Zoom de Escala + Sandbox What-If") y reparto humano/agente.
- **[`SYLLABUS_MAP.md`](../SYLLABUS_MAP.md)** - Radar vivo de cobertura de los 9 bloques del temario 5G (`T1`–`T9`).
- **[`course-notes/`](../course-notes/)** - Requisitos y apuntes tecnicos de asignatura universitaria (entrada normativa para specs).
- **[`REFERENCES.md`](../REFERENCES.md)** - Ecosistema, librerias oraculo, fuentes de datos de Espana y patrones MapLibre/deck.gl.

---

## 3. Modulos del Sistema (`modules/`)
Registro de fichas tecnicas de cada modulo implementado en el proyecto.
- **[`rf-antenna-and-propagation-engine.md`](modules/rf-antenna-and-propagation-engine.md)** - Mallado `5m/12m/50m` con relieve 3D, antenas `UPA` 3GPP TR 38.901, propagacion (`UMa`/`UMi`), *shadow fading* 2D correlado, cobertura `SS-RSRP`, ruido termico por `RE` y `SINR` co-canal en `mW`.
- **[`jaen-gis-and-data-sources.md`](modules/jaen-gis-and-data-sources.md)** - Proyeccion `EPSG:4326 <-> EPSG:25830`, muestreo de relieve `MDT05` y fusion OpenCelliD (`MCC=214`) + mastiles OSM en `data/cities/jaen.yaml` (`Red A/B/C` sobre bloques CNAF).
