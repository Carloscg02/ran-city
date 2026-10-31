# RAN City — Visión del proyecto

> **Estado**: visión aterrizada y gobernanza activa con `compass-harness`. Documento vivo.
> **Nombre**: `RAN-city` (ciudad inicial: **Jaén**; después **Málaga** por configuración).

---

## 1. Qué es y por qué existe

**RAN City** es un **banco de pruebas interactivo y proyecto personal de aprendizaje** para entender en profundidad las redes móviles 5G NR sobre el mapa real de una ciudad.

Su metáfora central es un **"Zoom de Escala + Sandbox What-If"**:
1. Arrancas en la **escala de ciudad (`km`)** sobre Jaén viendo su relieve, edificios y una **red base estimada** a partir de datos abiertos legales (**OpenCelliD `MCC=214`** agrupado por `MNC` bajo alias neutros **`Red A / B / C`** sobre bloques reales del **CNAF**, cruzado con mástiles **OpenStreetMap** y completado donde haga falta con sitios `synthetic` etiquetados).
2. Sobre esa foto base puedes hacer experimentos **What-If** (modificar *tilt*, potencia o banda `n28`/`n78`/`n258`, apagar un emplazamiento o desplegar uno nuevo, y pulsar *Reset* para volver a la red base).
3. Al hacer click en cualquier elemento haces **zoom de escala** mediante inspectores que combinan controles en vivo con **explicaciones físicas/3GPP breves e integradas**:
   - **Escala Antena (`°` / haces)**: patrón 3GPP TR 38.901, *array factor* Massive MIMO y *tilt* mecánico/eléctrico conectado directamente a la huella en el mapa.
   - **Escala Celda / Capa Física (`ms` / `RB`)**: *link budget*, numerología NR, *resource grid* y cadena `SINR → CQI/MCS → Throughput`.
   - **Escala UE / Movilidad y Protocolos (`eventos` / `mensajes`)**: UE recorriendo calles reales con medidas en vivo, handovers (`A3`/`B1`) y *call flows* contextuales.
   - **Escala Red / Operación (`periodos PM`)**: contadores 3GPP, KPIs y diagnóstico de celdas degradadas.

### Objetivos (por orden de prioridad)

1. **Aprender en profundidad.** El proyecto es el vehículo para dominar el temario de formación en 5G RAN (sección 4 y seguimiento detallado en [`docs/SYLLABUS_MAP.md`](docs/SYLLABUS_MAP.md)). Cada bloque implica entender la física, el protocolo o la métrica que hay detrás.
2. **Tener algo propio que crezca con un hilo conductor coherente.** Construimos primero la columna vertebral (*Antena → Cobertura → Celda NR → UE en ruta → KPIs*) sin meter temas con calzador, manteniendo el resto del temario inventariado para incorporarlo cuando sume de verdad.
3. **Servir de portfolio.** Funciona en vivo contra el backend Python (local o deploy ligero) e incluye un modo de exportación de escenarios precalculados para mantener siempre disponible un enlace estático de demostración.
4. **Desarrollarlo con IA de forma disciplinada (`compass-harness`).** Usar Spec-Driven Development (`SDD`), TDD en *seams* públicos y validación de invariantes físicos sin que la IA sustituya mi comprensión (sección 9).

### Lo que NO es

- No es una herramienta comercial de planificación radio ni pretende sustituir mediciones certificadas.
- No usa información confidencial de ninguna empresa ni marcas comerciales de operadores: solo especificaciones públicas (3GPP, ITU), literatura abierta y datos públicos con licencia reutilizable.
- No presenta estimaciones o simulaciones como mediciones reales: toda entidad y capa muestra su etiqueta `real` | `estimated` | `synthetic`.

---

## 2. Principios de diseño

| Principio | Qué significa en la práctica |
|---|---|
| **Python como núcleo (Hexagonal)** | Toda la lógica (antenas, propagación, capa física, protocolos, movilidad, KPIs y geoprocesamiento) vive en Python puro sin acoplarse a FastAPI ni a la UI. |
| **Escudo de tipos y coordenadas** | Tipos explícitos para `dBm`/`dB`/`mW`, azimut brújula (`0° = Norte` horario) y cenital 3GPP (`90° = horizonte`). Cálculo interno siempre en `EPSG:25830` (metros); `EPSG:4326` solo en la frontera I/O. |
| **Frontend ligero y rápido** | TypeScript + React + MapLibre GL JS + `deck.gl` (`BitmapLayer` raster sobre `OpenFreeMap` / `PMTiles`). Cero lógica física duplicada en TS y cero rejillas masivas en GeoJSON. |
| **Primero correcto, luego bonito** | Cada fórmula cita su sección 3GPP/ITU y se valida con tests de valores de referencia + *Property-Based Testing* (`hypothesis`). |
| **Explicable** | Cada inspector incluye cápsulas concisas del *"por qué físico / estándar"* para servir tanto de herramienta de repaso como de portfolio autoexplicativo. |
| **Documentar lo aprendido** | Cada hito se acompaña de guías didácticas cualitativas en `guides/<slug>-GUIDE.md` (`mentor-guide`) y preguntas de comprobación conceptual. |

---

## 3. Por qué Jaén primero (y Málaga después)

- **Jaén**: relieve muy marcado (Cerro de Santa Catalina frente al desnivel norte-sur, ideal para comprobar sombra topográfica y *tilt*), contraste fuerte entre casco histórico estrecho, ensanche/Bulevar y polígonos industriales, y tamaño manejable para iterar rápido.
- **Málaga** después: entorno costero, alta densidad urbana, recintos de gran demanda (estadio, centro, PTA) y escenario ideal para `mmWave (26 GHz)` y `FWA`. Añadir una ciudad debe consistir en añadir su fichero `data/cities/<ciudad>.yaml` y ejecutar la ingesta.

---

## 4. Temario de referencia y seguimiento (`T1`–`T9`)

El índice completo de los 9 bloques de formación (**T1 Air Interface**, **T2 RAN Protocol & Procedures**, **T3 NR KPIs**, **T4 Antenna Systems**, **T5 Voice over NR**, **T6 Network Slicing**, **T7 Multi-layer Coordination & Load Balancing**, **T8 FWA** y **T9 NR High-Band mmWave**) y el estado vivo de cada subapartado se mantienen en **[`docs/SYLLABUS_MAP.md`](docs/SYLLABUS_MAP.md)**.

- **Arranque acordado**: **T4 + T1 base** (Modelado de antenas según **3GPP TR 38.901** + *Link Budget* / `RSRP` / `SINR`), conectando la física de radiación directamente con la cobertura sobre Jaén.

---

## 5. Estrategia de datos: qué es público y qué se simula

Verificación detallada de fuentes y licencias registrada en **[`docs/REFERENCES.md`](docs/REFERENCES.md)**:

| Dato | Fuente adoptada | Estrategia |
|---|---|---|
| **Mapa base y callejero** | **OpenFreeMap** / **PMTiles (Protomaps)** sobre datos **OpenStreetMap** (ODbL) | Libre, sin API keys y exportable a un único archivo `.pmtiles` estático. |
| **Emplazamientos móviles** | **OpenCelliD (`MCC=214`)** (CC BY-SA 4.0) + mástiles **OSM** | Agrupación de celdas por sitio y separación por `MNC` bajo alias neutros **`Red A / B / C`** para simular interferencia co-canal intra-operador realista. Huecos cubiertos con sitios `synthetic`. *(Infoantenas descartado al no ofrecer API/WFS abierto).* |
| **Relieve (DEM)** | **CNIG / IGN (`MDT05` / `MDT02` COG)** | Lectura directa con `rasterio` en `EPSG:25830` para cota de estaciones y difracción por terreno. |
| **Edificios y alturas** | **Overture Maps / EUBUCCO / Catastro INSPIRE** | Huellas y alturas armonizadas para entorno urbano y visualización 3D. |
| **Espectro y configuración RF** | **CNAF** + valores típicos 3GPP documentados | Portadoras realistas (`n28` 700 MHz, `n78` 3.5 GHz, `n258` 26 GHz) configurables en el sandbox *What-If*. |
| **Mediciones de campo (futuro)** | **`TowerCollector`** (Android open-source) | Exportación CSV/GeoJSON propia para comparar paseo real vs. modelo en `M10`. |

---

## 6. Hoja de ruta modular (Hilo Conductor + Extensiones)

### Hilo Conductor Principal
1. **Fase 1 — Núcleo RF & Antenna Lab (`M1` + cimiento `M0` — `T4`, `T1 base`)**:
   - Tipos de valor RF (`dBm`/`mW`, azimut, cenital 3GPP), modelo de dominio (`Site`, `Sector`, `Cell`, `Antenna`, `Band`), patrón de elemento y *array factor* plano **3GPP TR 38.901**, *tilt* mecánico/eléctrico y *link budget* puntual verificados con `pytest` + `hypothesis`.
2. **Fase 2 — Jaén Base, Red Estimada y Cobertura (`M0` + `M2` — `T1`, `T4`)**:
   - Config `data/cities/jaen.yaml`, ingesta reproducible OpenCelliD (`Red A/B/C`) + OSM + MDT05, modelos `UMa`/`UMi`/`RMa` + difracción topográfica *Knife-Edge*, rejilla vectorizada `NumPy → PNG` y mapa interactivo MapLibre + `deck.gl` con sandbox *What-If* e inspector de Antena conectado.
3. **Fase 3 — Inspector de Celda NR / Air Interface (`M3` — `T1`)**:
   - Numerología NR, *resource grid* (`SSB`, `PDSCH`, `PDCCH`, `DMRS`), patrones TDD y cadena `SINR → CQI/MCS → Throughput` contextualizada sobre cualquier celda/punto de Jaén.
4. **Fase 4 — UE en Ruta, Movilidad Multicapa y Protocolos (`M5` + `M4` — `T2`, `T7`)**:
   - UE desplazándose por calles reales de Jaén sobre capas `LTE` + `NR` (`n28`/`n78`), eventos `A3`/`A5`/`B1` con histéresis/TTT, handovers y *stepper* de señalización contextual (`RACH → RRC Setup → Registration → PDU Session`).
5. **Fase 5 — Operación, Contadores PM y KPIs (`M6` — `T3`)**:
   - Generación de contadores sintéticos 3GPP TS 28.552, panel de KPIs e inyección *What-If* de fallos (*site down*, mal *tilt*, sobrecarga) para practicar *troubleshooting*.

### Extensiones Posteriores (según avance del estudio en `SYLLABUS_MAP.md`)
- **`M4+` VoNR (`T5`)**: Escenarios de llamada `VoNR` y *EPS Fallback* en el inspector de protocolos.
- **`M7` Network Slicing (`T6`)**: Particionado de recursos `PRB` entre `eMBB` y `URLLC`.
- **`M8` FWA Planner (`T8`)**: Cobertura/capacidad de hogares y CPE *indoor*/*outdoor* sobre edificios de Jaén/Málaga.
- **`M9` mmWave & Tuning (`T9`)**: Banda `n258` (26 GHz), bloqueo urbano y opción de *ray tracing* con `NVIDIA Sionna RT`.
- **`M10` Datos de campo propios** (`TowerCollector`) y **`M11` Red 5G local** (`Open5GS` + `UERANSIM` + decodificación ASN.1 con `pycrate`).

---

## 7. Estructura del repositorio (integrada con `compass-harness`)

```text
RAN-city/
├── AGENTS.md                      # Router principal de Compass Harness (< 100 líneas)
├── VISION.md                      # Visión funcional y pedagógica (este documento)
├── .compass/skills/               # Fuente de verdad de skills (tdd, sdd-workflow, ui-design, mentor-guide...)
├── backend/
│   ├── ran_city/
│   │   ├── domain/                # Tipos RF (Dbm, AzimuthDeg...), Site, Sector, Cell, Antenna, Band
│   │   ├── antenna/               # Patrón de elemento TR 38.901, array factor, tilt, beamforming
│   │   ├── radio/                 # Path loss, difracción MDT, link budget, RSRP, SINR
│   │   ├── air_interface/         # Numerología, resource grid, TDD, MCS/CQI, throughput
│   │   ├── protocols/             # Máquinas de estado y escenarios de señalización
│   │   ├── mobility/              # Eventos A3/A5/B1, histéresis/TTT, handover multicapa
│   │   ├── kpis/                  # Contadores PM y fórmulas 3GPP TS 28.552
│   │   ├── geo/                   # Transformaciones EPSG:25830/4326, MDT05, edificios, rasters PNG
│   │   ├── data_sources/          # Importador OpenCelliD/OSM (Red A/B/C), generador sintético y export estático
│   │   └── api/                   # Adaptador HTTP fino con FastAPI (OpenAPI tipado)
│   ├── tests/                     # Tests en seams públicos (pytest + hypothesis)
│   └── pyproject.toml
├── frontend/                      # TypeScript + React + Vite + MapLibre GL + deck.gl
├── data/
│   ├── cities/jaen.yaml           # Bounding box, CRS, bandas CNAF y fuentes
│   └── cache/                     # Descargas y procesados locales (gitignored)
├── docs/
│   ├── brain/                     # Memoria jerárquica viva de Compass (index, architecture, handoff, decisions, design)
│   ├── SYLLABUS_MAP.md            # Seguimiento completo de los 9 bloques T1–T9
│   ├── REFERENCES.md              # Ecosistema, librerías oráculo y referencias 3GPP/GIS
│   └── course-notes/              # Apuntes y requisitos técnicos de asignatura universitaria
├── specs/                         # Especificaciones SDD por feature (spec.md -> plan.md -> tasks.md)
└── guides/                        # Guías didácticas bajo demanda generadas por mentor-guide
```

---

## 8. Calidad y validación

- **Tests con trazabilidad bibliográfica**: cada cálculo en Python cita especificación + sección/tabla y se prueba frente a valores calculados a mano o tablas de referencia.
- **Invariantes físicos con `hypothesis`**: comprobación automática de monotonía, cotas de ganancia/atenuación, simetría geométrica y suma lineal en `mW`.
- **Contraste opcional con oráculos**: uso puntual en entorno de estudio de librerías independientes (`py3gppchannels`, `pycraf`, `py3gpp`) sin acoplarlas al código de producción.
- **Atribución visible en la UI**: OpenStreetMap, OpenCelliD, IGN/CNIG y fuentes catastrales/edificios claramente acreditadas.

---

## 9. Cómo quiero aprender (instrucción explícita para el agente IA)

### Reparto de trabajo
- **El agente se encarga de**: andamiaje, configuración, pipelines geoespaciales, boilerplate de FastAPI, UI React/MapLibre/deck.gl, refactors e infraestructura de tests.
- **Yo implemento (o reviso y valido línea a línea)**: el núcleo de dominio 5G (patrones de antena, ecuaciones de propagación, `SINR`, *resource grid*, máquinas de estado de protocolos, lógica de handover y fórmulas de KPIs).

### Reglas operativas en cada módulo (`SDD`)
1. Antes de implementar lógica de dominio 5G, explicar el concepto físico/protocolar, citar las fuentes públicas (3GPP/ITU) y consensuar el diseño en `spec.md` / `plan.md`.
2. Prohibido inventar constantes o fórmulas: citar siempre sección/tabla o declarar explícitamente cualquier simplificación asumida.
3. Nada de información confidencial ni marcas comerciales de operadores.
4. Al cerrar cada módulo: actualizar [`docs/SYLLABUS_MAP.md`](docs/SYLLABUS_MAP.md), generar guía didáctica intuitiva en `guides/<slug>-GUIDE.md` si se solicita, y plantearme preguntas cualitativas de comprobación conceptual.
5. Registrar decisiones arquitectónicas relevantes como ADRs en [`docs/brain/decisions/`](docs/brain/decisions/index.md).
