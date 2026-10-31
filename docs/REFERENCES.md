# Referencias Técnicas, Ecosistema y Buenas Prácticas (`RAN-city`)

> Documento vivo de referencia con el software open-source, fuentes geoespaciales verificadas de España, estándares 3GPP/ITU y patrones de ingeniería seleccionados antes de arrancar la implementación.

---

## 1. Estándares Públicos de Referencia (Fuentes Primarias)

Toda ecuación o máquina de estado implementada en `backend/ran_city/` debe citar su sección o tabla exacta en una fuente pública:

- **3GPP TR 38.901** *(Study on channel model for frequencies from 0.5 to 100 GHz)*:
  - Sección 7.1: Sistema de coordenadas global/local y definición de ángulo cenital (`θ = 90°` en el horizonte) y azimut (`φ`).
  - Sección 7.3: Patrón de radiación de elemento de antena (`G_E,max = 8 dBi`, `SLA_v = 30 dB`, `A_max = 30 dB`, `θ_3dB = 65°`, `φ_3dB = 65°`) y modelado de paneles planos (`N_V × N_H`).
  - Sección 7.4: Modelos de *path loss*, probabilidad de `LOS` y *shadow fading* para `UMa`, `UMi - Street Canyon` y `RMa`.
- **3GPP TS 38.101-1 / 38.101-2 / 38.104**: Bandas operativas NR (`n28`, `n78`, `n258`), anchos de banda de canal, espaciado de subportadoras y niveles de referencia BS/UE.
- **3GPP TS 38.211 / 38.214**: Numerología OFDM (`μ = 0..4`), estructura de trama/slot, *Resource Grid*, `SSB` y tablas `CQI` / `MCS` / cálculo de *Transport Block Size*.
- **3GPP TS 38.306**: Cálculo aproximado de *throughput* máximo de datos NR.
- **3GPP TS 38.331 / TS 38.413 / TS 24.501**: Protocolos `NR RRC` (incluyendo eventos de medida `A1–A6`, `B1–B2`), `NGAP` y `5G NAS`.
- **3GPP TS 28.552**: Definición oficial de contadores de *Performance Management* y fórmulas de KPIs 5G NR.
- **ITU-R Rec. P.526**: Propagación por difracción (*Knife-Edge* / método de Bullington sobre perfiles de terreno).
- **CNAF (España)**: Cuadro Nacional de Atribución de Frecuencias para parametrizar concesiones realistas en `700 MHz (n28)`, `3.5 GHz (n78)` y `26 GHz (n258)`.

---

## 2. Proyectos Similares y Referencias Visuales

- **`Cloud-RF/Signal-Server`** (`https://github.com/Cloud-RF/Signal-Server`, GPLv2): Fork multihilo de SPLAT! en C++ para cálculo de cobertura sobre DEM con Longley-Rice (ITM). Útil como referencia conceptual de rasters RF, descartado como motor por no modelar 5G NR/AAS y por su licencia GPLv2.
- **`komelt` Web RF Planner** y **`heimiricmr` Cellular RF Workspace**: Validan el patrón arquitectónico *Backend de cálculo → Raster ligero → MapLibre GL*.
- **`mbebs/RFTools`** (`https://github.com/mbebs/RFTools`, QGIS Python): Referencia visual de ingeniería celular para geometría de sectores multibanda, dominancia y análisis de `PCI` en `n78`.
- **`rotemTsafrir/dipole_sim`** (`https://www.antennasim.com`, `https://github.com/rotemTsafrir/dipole_sim`): Referencia de UX interactiva para visualización de arrays en fase y *beamforming* en tiempo real.
- **`zhang-stephen/nr_visualizer`** y **`ClaudinaRattaro/Py5cheSim`**: Referencias ligeras en Python para visualización declarativa de *resource grids* Rel-16 y simulación de *slicing*.
- **Recursos didácticos abiertos**: **[PySDR](https://pysdr.org/)** (Marc Lichtman) y **ShareTechnote 5G NR**.

---

## 3. Librerías Python Reutilizables (Política de 3 Roles)

Para proteger el objetivo principal del proyecto (**aprender implementando el dominio**), las librerías externas se dividen en tres categorías estrictas:

### 3.1 Rol A — Oráculos de Validación (Solo en entorno de estudio/contraste, fuera del núcleo)
- **`zilligm/py3gppchannels`** (`https://github.com/zilligm/py3gppchannels`) y **`AmbitiousWarrior/3GPP_Channel_Model`**: Implementaciones Python de **3GPP TR 38.901** útiles para contrastar resultados numéricos de *path loss* y probabilidad `LOS`.
- **`bwinkel/pycraf`** (`https://github.com/bwinkel/pycraf`, GPLv3) e **`itur`**: Implementan recomendaciones ITU-R (`P.452`, gases `P.676`, antenas IMT-2020 `M.2136`). Por licencia GPLv3 en `pycraf`, no se importa ni distribuye nunca dentro del paquete `ran_city`.
- **`catkira/py3gpp`** (`https://github.com/catkira/py3gpp`): Equivalente en NumPy al *5G Toolbox* de MATLAB para contrastar índices de canales físicos (`SSB`/`PBCH`) en `M3`.

### 3.2 Rol B — Física Auxiliar de Terreno
- **Difracción sobre MDT05**: TR 38.901 no detecta obstrucciones topográficas deterministas (como el Cerro de Santa Catalina en Jaén). Se complementa leyendo perfiles de elevación con `rasterio` y aplicando difracción *Knife-Edge* (ITU-R P.526) propia o comparando frente a **`edwardoughton/itmlogic`** (`https://github.com/edwardoughton/itmlogic`, MIT, Longley-Rice en Python puro).

### 3.3 Rol C — Aceleradores para Módulos Avanzados Futuros
- **`NVlabs/sionna` (`sionna.rt`)** (`https://github.com/NVlabs/sionna`, Apache 2.0): Motor de *Ray Tracing* 3D sobre escenas reales de OpenStreetMap (Mitsuba 3). Candidato para **`M9 — mmWave (26 GHz)`**.
- **`pycrate-org/pycrate`** (`https://github.com/pycrate-org/pycrate`, LGPL-2.1): Codificador/decodificador ASN.1 real de mensajes **NR RRC**, **NGAP** y **5G NAS**. Candidato para **`M4` (Protocol Stepper)** y **`M11` (Open5GS + UERANSIM)**.
- **`zamojski/TowerCollector`** (`https://github.com/zamojski/TowerCollector`, MPL-2.0, F-Droid): App Android open-source con soporte **5G NR** que exporta CSV/GeoJSON y sube medidas a OpenCelliD; evita desarrollar una app móvil desde cero en **`M10`**.

---

## 4. Fuentes de Datos Abiertos Verificadas para España (Jaén / Málaga)

| Capa | Fuente elegida | Estado legal / técnico verificado |
|---|---|---|
| **Emplazamientos móviles (`estimated`)** | **OpenCelliD (`MCC=214`)** + **OSM (`man_made=mast`, `communication:mobile_phone`)** | **Viable (CC BY-SA 4.0 + ODbL)** con atribución visible. OpenCelliD ofrece el centroide de mediciones por celda; agrupando sectores y cruzando con mástiles OSM se estiman sitio y azimuts. *(Nota: `beaconDB` aún no publica dumps completos).* |
| **Visor Infoantenas (Ministerio)** | **Descartado** | Verificado: no dispone de servicio WFS ni API de datos abiertos para descarga/reutilización automatizada (consulta puntual ciudadana sobre RENAFE). |
| **Relieve (DEM)** | **CNIG / IGN (`MDT05` / `MDT02`)** | Disponible como **COG (*Cloud Optimized GeoTIFF*)** en `ETRS89 / UTM 30N` (`EPSG:25830`), licencia abierta CC BY 4.0 IGN. |
| **Edificios y alturas** | **Overture Maps (`GeoParquet`) / EUBUCCO / Catastro INSPIRE** | Overture y EUBUCCO ofrecen huellas y alturas armonizadas (derivadas de OSM y Catastro) listas para consultar sin parsear GML complejos de inicio; Catastro INSPIRE (`BU.Building`) queda disponible para detalle municipal fino. |
| **Mapa base vectorial** | **OpenFreeMap** + **PMTiles (Protomaps)** | 100% libre y sin API keys. Un recorte `.pmtiles` de Jaén (~10 MB) permite servir el mapa estático sin servidor de tiles mediante *HTTP Range Requests*. |

---

## 5. Patrones de Mapas Web y Desarrollo con Agentes de IA

1. **Renderizado de Cobertura (`NumPy → PNG → deck.gl BitmapLayer`)**:
   - Evaluar rejillas `float32` vectorizadas en Python sobre **`EPSG:25830`** y exportarlas como `PNG` RGBA + *bounding box* WGS84 para `@deck.gl/maplibre` (`MapLibreOverlay` con `interleaved: true`). Nunca enviar mallas densas como polígonos GeoJSON.
2. **Skills Oficiales de MapLibre**:
   - Consultar **`maplibre/maplibre-agent-skills`** (`https://github.com/maplibre/maplibre-agent-skills`) al abrir tareas de frontend cartográfico para evitar mezclar APIs heredadas de Mapbox v1 o añadir capas fuera de `map.on('load')`.
3. **Verificación de Simulaciones Físicas con Agentes (`pytest` + `hypothesis`)**:
   - Complementar los tests de tabla 3GPP con propiedades invariantes en `hypothesis` (monotonía con la distancia, cotas máximas/mínimas de ganancia y atenuación, simetría rotacional de azimut y conversión estricta `dBm ↔ mW`).
4. **Testing E2E de WebGL (`Agent Eyes`)**:
   - Validar paneles, controles, leyendas y cápsulas 3GPP mediante `ariaSnapshot()` de Playwright (cubriendo los 4 estados: `Loading`, `Empty`, `Error`, `Populated`), mockear peticiones de tiles en tests y exponer atributos `data-map-loaded` junto a cero errores de consola/WebGL.
