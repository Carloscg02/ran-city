# Spec 002: Completitud de Link Budget 5G (`SINR`, Ruido Térmico, *Shadow Fading*) e Ingesta GIS de Jaén (`002-sinr-link-budget-and-jaen-gis`)

- **Estado**: Aprobado
- **Modalidad de Ejecución Confirmada**: **Modo 2 — Co-implementación guiada** en dominio 5G (`radio`, `domain`) + delegación en `subagent-fast` (`flash`) para andamiaje y pipelines GIS (`geo`, `data_sources`)
- **Fuentes Curriculares**:
  - Temario 5G RAN: `T1` (*Air Interface — Link Budget completo: ruido térmico, interferencia co-canal en mW y SINR*) + `T4` (*Antenna Systems — impacto de tilts y relieve real sobre dominancia celular y SINR*)
  - Asignatura Planificación de Redes: [`docs/course-notes/001_propagacion_mallado_T2.md`](../../docs/course-notes/001_propagacion_mallado_T2.md) (evaluación matricial sobre mallas por entorno `5 m / 12 m / 50 m`, prohibición de `FSPL` como cobertura final y desacoplo de matrices de propagación y antena)
  - Decisiones Arquitectónicas: [ADR 0001](../../docs/brain/decisions/0001-initial-architecture.md), [ADR 0002](../../docs/brain/decisions/0002-rf-domain-and-map-guardrails.md), [ADR 0003](../../docs/brain/decisions/0003-tr38901-propagation-matrix.md)
- **Carril**: `SDD` — Fase 1 (`spec.md`)

---

## 1. Contexto y Propósito

Con el motor matricial de antenas y propagación **3GPP TR 38.901** operativo en la `Spec 001` (`SS-RSRP` y `Best Server`), esta segunda especificación cierra dos pilares esenciales antes de levantar la API y el visor cartográfico:

1. **Completar el *Link Budget* 5G NR en el dominio radio (`ran_city.radio`)**:
   - Incorporar el **ruido térmico del receptor UE** ($k_B T_0 B F$) coherente con la potencia por *Resource Element* (`RE`).
   - Incorporar el **desvanecimiento lento por sombra (*Shadow Fading*, `SF`)** log-normal y **espacialmente correlado en 2D** según **3GPP TR 38.901** (`Table 7.4.1-1` y `Table 7.5-6`), activable de forma reproducible mediante semilla.
   - Calcular la matriz de **`SINR` co-canal multicelda** convirtiendo estrictamente las potencias recibidas de `dBm` a milivatios lineales (`LinearMw` / `mW`), aislando la interferencia co-canal por **operador (`Red A / B / C`)** y por **portadora/banda NR (`n28`, `n78`, `n258`)**.
2. **Aterrizar el motor sobre la geografía y red estimada real de Jaén (`ran_city.geo`, `ran_city.data_sources`, `data/cities/jaen.yaml`)**:
   - Exponer en `ScenarioGrid` el soporte para una **matriz 2D de elevación del terreno (`terrain_z_m`)** en `EPSG:25830`, de modo que las distancias 3D y los ángulos cenitales $\Theta_{\text{GCS}}$ reflejen el fuerte desnivel real de Jaén (Cerro de Santa Catalina a ~`815 m` frente al Bulevar a ~`430 m`).
   - Construir los adaptadores geoespaciales para leer el Modelo Digital del Terreno **`MDT05` del CNIG/IGN**, descargar y filtrar las celdas reales de **OpenCelliD (`MCC=214`)** en Jaén (usando `OPENCELLID_API_KEY` por entorno), cruzarlas con los **mástiles de OpenStreetMap** y persistir el escenario completo en **`data/cities/jaen.yaml`** bajo alias neutros (`Red A`, `Red B`, `Red C`) con trazabilidad `source: "estimated" | "synthetic"`.

---

## 2. Formulación Matemática Exacta y Fuentes Públicas

### 2.1 Ruido Térmico por *Resource Element* (`RE`) y de Canal — *3GPP TS 38.101-1 v17.8.0 Clause 7.3 & TS 38.104*

1. **Densidad espectral de ruido térmico de Johnson-Nyquist**:
   Con la constante de Boltzmann exacta $k_B = 1.380649 \times 10^{-23}\text{ J/K}$ y temperatura de referencia $T_0 = 290.0\text{ K}$:
   $$N_0 = 10\log_{10}\left(k_B \cdot T_0 \cdot 1000\text{ mW/W}\right) \approx -173.97519\text{ dBm/Hz}$$
2. **Coherencia de ancho de banda con `RSRP` por `RE`**:
   En **3GPP TS 38.215 Clause 5.1.1**, la potencia recibida de referencia $\mathbf{RSRP}_k$ se define sobre un único *Resource Element* (`1 RE = 1 subportadora`). Para mantener consistencia dimensional en la relación $\text{SINR} = \frac{S_{\text{RE}}}{I_{\text{RE}} + N_{\text{RE}}}$, el ruido térmico por `RE` se integra sobre el ancho de banda de una subportadora $B_{\text{RE}} = \Delta f_{\text{SCS}} = \text{scs\_khz} \times 10^3\text{ Hz}$ y suma la figura de ruido del terminal $F_{\text{UE}}$ (en `dB`, típicamente $F_{\text{UE}} = 9.0\text{ dB}$ en FR1 según *3GPP TR 38.802 Table A.2.1-1 / TS 38.101-1*):
   $$N_{\text{RE (dBm)}} = 10\log_{10}\left(k_B \cdot T \cdot 1000\right) + 10\log_{10}\left(\Delta f_{\text{SCS, Hz}}\right) + F_{\text{UE (dB)}}$$
   - Valores de referencia a $T = 290.0\text{ K}$ y $F_{\text{UE}} = 9.0\text{ dB}$:
     - Banda `n28` ($\Delta f_{\text{SCS}} = 15\text{ kHz}$): $N_{\text{RE}} = -173.97519 + 41.76091 + 9.0 = -123.21427\text{ dBm}$.
     - Banda `n78` ($\Delta f_{\text{SCS}} = 30\text{ kHz}$): $N_{\text{RE}} = -173.97519 + 44.77121 + 9.0 = -120.20397\text{ dBm}$.
     - Banda `n258` ($\Delta f_{\text{SCS}} = 120\text{ kHz}$): $N_{\text{RE}} = -173.97519 + 50.79181 + 9.0 = -114.18337\text{ dBm}$.
3. **Potencia de ruido total del canal (`N_RB` bloques de `12` subportadoras)**:
   Para cálculos de presupuesto de enlace de banda completa ($B_{\text{ch}} = 12 \cdot N_{\text{RB}} \cdot \Delta f_{\text{SCS, Hz}}$):
   $$N_{\text{ch (dBm)}} = N_{\text{RE (dBm)}} + 10\log_{10}\left(12 \cdot N_{\text{RB}}\right)$$

### 2.2 *Shadow Fading* Log-Normal Espacialmente Correlado 2D — *3GPP TR 38.901 v17.1.0 Clauses 7.4.1 (Table 7.4.1-1), 7.4.4 & Table 7.5-6*

1. **Parámetros normativos 3GPP por modelo y estado `LOS / NLOS`**:
   | Modelo (`CellType`) | $\sigma_{\text{SF,LOS}}$ (`Table 7.4.1-1`) | $\sigma_{\text{SF,NLOS}}$ (`Table 7.4.1-1`) | $d_{\text{cor,LOS}}$ (`Table 7.5-6`) | $d_{\text{cor,NLOS}}$ (`Table 7.5-6`) |
   |---|---|---|---|---|
   | **`UMa`** (`MACRO`) | $4.0\text{ dB}$ | $6.0\text{ dB}$ | $37.0\text{ m}$ | $50.0\text{ m}$ |
   | **`UMi - Street Canyon`** (`MICRO` / `PICO`) | $4.0\text{ dB}$ | $8.2\text{ dB}$ | $10.0\text{ m}$ | $13.0\text{ m}$ |

2. **Síntesis 2D correlada con preservación exacta de varianza**:
   Sobre una malla `ScenarioGrid` de paso $\Delta_{\text{grid}} \in \{5, 12, 50\}\text{ m}$, para cada estado $s \in \{\text{LOS}, \text{NLOS}\}$:
   - Se genera una realización normal estándar $\mathbf{W}_s \sim \mathcal{N}(0, 1)$ de tamaño $(N_y, N_x)$ mediante `np.random.default_rng(seed)`.
   - Se aplica un filtro espacial gaussiano 2D con escala en píxeles $\sigma_{\text{px}, s} = \frac{d_{\text{cor}, s}}{\Delta_{\text{grid}}}$.
   - Como el suavizado discreto con kernel $\mathbf{K}_s$ reduce la varianza por el factor $\|\mathbf{K}_s\|_2^2 = \sum_{u,v} K_s(u,v)^2$, el campo filtrado se divide analíticamente por $\|\mathbf{K}_s\|_2$ para garantizar $\operatorname{Var}[\mathbf{Z}_s(y,x)] = 1.0$ en todo píxel, y finalmente se escala por $\sigma_{\text{SF}, s}$:
     $$\mathbf{SF}(y, x) = \begin{cases} \sigma_{\text{SF,LOS}} \cdot \mathbf{Z}_{\text{LOS}}(y, x), & \text{si } \text{los\_mask}(y, x) = \text{True} \\ \sigma_{\text{SF,NLOS}} \cdot \mathbf{Z}_{\text{NLOS}}(y, x), & \text{si } \text{los\_mask}(y, x) = \text{False} \end{cases}$$
   - Cuando está activo (`include_shadow_fading=True`), el mapa $\mathbf{SF}$ se suma en `dB` a la pérdida de propagación:
     $$\mathbf{L}_{\text{prop, total}} = \mathbf{L}_{\text{prop, median}} + \mathbf{SF}$$

### 2.3 Interferencia Co-Canal Intra-Operador y `SINR` en `mW` — *3GPP TS 38.215 Clause 5.1.3 & ADR 0002*

1. **Aislamiento espectral por Operador (`network_alias`) y Banda (`n_band`)**:
   - Dos celdas solo interfieren de forma co-canal si pertenecen a la **misma red activa** (`site.network_alias`, ya que cada operador dispone de su propia concesión CNAF) **y** operan en la **misma banda/portadora** (`cell.band.n_band`).
   - En un escenario con múltiples operadores o múltiples capas (`n28` + `n78`), el cálculo de cobertura/SINR filtra primero el subconjunto activo $\mathcal{C}(R, B)$ para la red $R$ (si se especifica) y banda $B$ (si se especifica).
2. **Suma lineal obligatoria en milivatios (`mW`)**:
   Para cada celda activa $k \in \{0, \dots, M-1\}$ del conjunto co-canal evaluado:
   $$\mathbf{S}_k(y, x) = 10^{\mathbf{RSRP}_k(y, x) / 10} \quad [\text{mW}]$$
   Si la celda servidora en el píxel $(y, x)$ es $k^*(y, x) = \arg\max_k \mathbf{RSRP}_k(y, x)$ y cada celda interferente $j \neq k^*(y, x)$ tiene factor de carga de tráfico $\eta_j \in [0.0, 1.0]$ (por defecto $\eta_j = 1.0$):
   $$\mathbf{I}_{\text{mW}}(y, x) = \sum_{j \neq k^*(y, x)} \eta_j \cdot \mathbf{S}_j(y, x), \qquad N_{\text{RE, mW}} = 10^{N_{\text{RE (dBm)}} / 10}$$
   $$\mathbf{SINR}_{\text{linear}}(y, x) = \frac{\mathbf{S}_{k^*(y,x)}(y, x)}{\mathbf{I}_{\text{mW}}(y, x) + N_{\text{RE, mW}}}, \qquad \mathbf{SINR}_{\text{dB}}(y, x) = 10\log_{10}\left(\mathbf{SINR}_{\text{linear}}(y, x)\right)$$

### 2.4 Cota Topográfica 3D (`MDT05`) sobre `ScenarioGrid` y `Site`

- En coordenadas proyectadas **`EPSG:25830` (`ETRS89 / UTM zone 30N`)**:
  - La estación transmisora del sector se ubica en $z_{\text{TX}} = z_{\text{ground, site}} + h_{\text{BS}}$.
  - Cada píxel $(y, x)$ de `ScenarioGrid` tiene cota absoluta de recepción $Z_{\text{RX}}(y, x) = Z_{\text{terrain}}(y, x) + h_{\text{UT}}$, donde $Z_{\text{terrain}}(y, x)$ proviene del ráster **CNIG `MDT05`** (o del plano constante `ground_z_m` si no se inyecta DEM).
  - La diferencia vertical $\Delta Z(y, x) = Z_{\text{RX}}(y, x) - z_{\text{TX}}$ alimenta directamente $D_{3\text{D}}(y, x) = \max\left(d_{\min}, \sqrt{D_{2\text{D}}(y, x)^2 + \Delta Z(y, x)^2}\right)$ y el ángulo cenital 3GPP $\Theta_{\text{GCS}}(y, x) = \arccos\left(\frac{\Delta Z(y, x)}{D_{3\text{D}}(y, x)}\right) \in [0^\circ, 180^\circ]$.

### 2.5 Ingesta y Fusión OpenCelliD (`MCC=214`) + Mástiles OSM + `MDT05` para Jaén

1. **Filtrado y atribución**:
   - **OpenCelliD (`MCC=214`)**: filtra celdas LTE/NR dentro del *bounding box* de Jaén (`EPSG:4326` en frontera de entrada $\rightarrow$ reproyectado inmediatamente a `EPSG:25830`).
   - **Mapeo de operador neutro y bloques CNAF**:
     - `MNC 07` $\rightarrow$ `Red A`
     - `MNC 01` $\rightarrow$ `Red B`
     - `MNC 03` $\rightarrow$ `Red C`
   - **Agrupación espacial y *snapping* a mástiles OSM**:
     - Las celdas del mismo operador situadas a menos de `cluster_radius_m` (por defecto `120 m`) se agrupan en un único emplazamiento (`Site`).
     - Si existe un mástil/torre de comunicaciones en OpenStreetMap (`man_made=mast`, `tower:type=communication` o `communication:mobile_phone=yes`) a menos de `osm_snap_radius_m` (`75 m`), la coordenada $(x_m, y_m)$ del sitio se ajusta a la posición física del mástil OSM.
     - Se asignan azimuts sectoriales coherentes (estimados por el vector sitio $\rightarrow$ muestra OpenCelliD o trisectorial estándar `0° / 120° / 240°`), cota `ground_z_m` muestreada del `MDT05` y etiqueta `source: DataSourceOrigin.ESTIMATED` (completando con sitios `DataSourceOrigin.SYNTHETIC` si alguna subzona de Jaén queda sin cobertura base).

---

## 3. Requerimientos Funcionales y Alcance

### Incluido en `Spec 002`
1. **Dependencias Geoespaciales y Científicas (`backend/pyproject.toml`)**:
   - Añadir `scipy>=1.12`, `pyproj>=3.6`, `rasterio>=1.3`, `pyyaml>=6.0` y `httpx>=0.27` mantendo `ran_city/{domain,antenna,radio}` libre de dependencias de I/O o GIS (`rasterio`/`pyproj`/`pyyaml`/`httpx` viven exclusivamente en `ran_city/{geo,data_sources}`).
2. **Terreno 3D en `ScenarioGrid` (`ran_city.domain.grid`)**:
   - Soporte para `terrain_z_m: np.ndarray | None = None` en `ScenarioGrid` (validando `shape == (n_y, n_x)` y ausencia de `NaN`/`inf`), método `with_terrain(terrain_z_m)` y cálculo vectorizado de $\Delta Z$, $D_{3\text{D}}$ y $\Theta_{\text{GCS}}$ sobre relieve variable.
3. ***Shadow Fading* 2D Correlado (`ran_city.radio.tr38901`)**:
   - Tablas normativas `shadow_fading_std_db(cell_type, is_los)` (`Table 7.4.1-1`) y `decorrelation_distance_m(cell_type, is_los)` (`Table 7.5-6`).
   - Función `sample_shadow_fading_map(cell_type, los_mask, resolution_m, seed)` y parámetro `include_shadow_fading: bool = False` en `compute_propagation_matrix` (exponiendo `shadow_fading_db: np.ndarray` dentro de `PropagationMatrix`).
4. **Ruido Térmico y `SINR` Co-Canal Multicelda (`ran_city.radio.coverage`)**:
   - Funciones `thermal_noise_dbm(bandwidth_hz, noise_figure_db=9.0, temperature_k=290.0) -> Dbm` y `re_thermal_noise_dbm(band: NrBand, noise_figure_db=9.0, temperature_k=290.0) -> Dbm`.
   - Extensión de `ScenarioCoverageResult` y `compute_scenario_coverage` con:
     - Filtrado opcional por `network_alias: str | None = None` y `n_band: int | None = None` (además de validación contra mezcla accidental de bandas o redes en el cálculo de interferencia co-canal).
     - Parámetros `ue_noise_figure_db: float = 9.0`, `cell_load_factor: float = 1.0` ($\eta \in [0, 1]$) e `include_shadow_fading: bool = False`.
     - Matrices de salida adicionales en `ScenarioCoverageResult`: `noise_per_re_dbm: float`, `interference_mw: np.ndarray`, `sinr_db: np.ndarray`.
5. **Adaptador Geoespacial y Relieve `MDT05` (`ran_city.geo`)**:
   - `crs.py`: `wgs84_to_utm30(lon, lat)` y `utm30_to_wgs84(x_m, y_m)` (`EPSG:4326 <-> EPSG:25830`).
   - `terrain.py`: `sample_points_elevation(raster_path, xs_m, ys_m)` y `sample_grid_terrain(raster_path, grid: ScenarioGrid) -> ScenarioGrid` sobre ficheros GeoTIFF/COG en `EPSG:25830`.
6. **Adaptador de Ingesta GIS y Escenario Jaén (`ran_city.data_sources`, `data/cities/jaen.yaml`)**:
   - Modelos de configuración de ciudad (`CityConfig`, `CityZoneSpec`, `OperatorSpectrumSpec`, `CityScenario`) y cargador/serializador YAML (`load_city_scenario`, `save_city_scenario`).
   - Pipeline de fusión `ingest_jaen.py`: descarga/parseo de celdas OpenCelliD (`MCC=214` en el BBox de Jaén usando `OPENCELLID_API_KEY` desde entorno), consulta de mástiles OSM (Overpass API / GeoJSON cacheado), muestreo de cota `MDT05` y generación de `data/cities/jaen.yaml` con emplazamientos `estimated` (y `synthetic` de respaldo donde proceda) para `Red A`, `Red B` y `Red C`.

### Fuera de Alcance (pospuesto a `Spec 003+`)
- Difracción topográfica *Knife-Edge* / Bullington (**ITU-R P.526-15**) sobre perfiles radiales `MDT05` y obstrucción determinista por edificios 3D de Catastro/Overture (`Spec 003`).
- Exportación de matrices a rasters `PNG` RGBA, endpoints HTTP `FastAPI` y visor interactivo `React + MapLibre GL + deck.gl` (`Spec 003`).
- Cadena `SINR -> CQI / MCS -> Throughput` y *Resource Grid* OFDM (`Fase 3 / M3`).

---

## 4. Criterios de Aceptación (CA)

- **CA-1 (Tooling y Aislamiento Hexagonal)**:
  - `backend/.venv/bin/pytest backend/tests` (incluyendo los 38 tests de `Spec 001` más los nuevos de `Spec 002`) y `backend/.venv/bin/ruff check backend` terminan con salida `0`.
  - Ningún módulo bajo `backend/ran_city/{domain,antenna,radio}` importa `rasterio`, `pyproj`, `yaml` ni `httpx`.
- **CA-2 (Ruido Térmico $k_B T_0 B F$ por `RE` y Canal)**:
  - A $T = 290.0\text{ K}$ y $F_{\text{UE}} = 9.0\text{ dB}$, `re_thermal_noise_dbm` devuelve `-123.2143 dBm` en `n28` (`15 kHz`), `-120.2040 dBm` en `n78` (`30 kHz`) y `-114.1834 dBm` en `n258` (`120 kHz`) con tolerancia `< 1e-4 dB`.
  - Duplicar el espaciado de subportadoras ($\Delta f_{\text{SCS}}$) incrementa el ruido por `RE` en exactamente `+3.0103 dB` ($10\log_{10} 2$).
- **CA-3 (*Shadow Fading* 2D Correlado según `TR 38.901`)**:
  - `shadow_fading_std_db` devuelve `4.0 / 6.0 dB` (`UMa` LOS/NLOS) y `4.0 / 8.2 dB` (`UMi` LOS/NLOS); `decorrelation_distance_m` devuelve `37.0 / 50.0 m` (`UMa`) y `10.0 / 13.0 m` (`UMi`).
  - Con la misma `seed`, `sample_shadow_fading_map` es 100% reproducible; en una malla grande, la media muestral es $\approx 0\text{ dB}$, la desviación típica muestral converge a $\sigma_{\text{SF}}$ gracias a la renormalización $\|\mathbf{K}\|_2$, y la autocorrelación entre píxeles adyacentes ($\Delta d = \Delta_{\text{grid}}$) es estrictamente positiva ($> 0.5$ cuando $\Delta_{\text{grid}} < d_{\text{cor}}$).
  - Por defecto (`include_shadow_fading=False`), `PropagationMatrix.shadow_fading_db` es una matriz de ceros y $\mathbf{L}_{\text{prop}}$ permanece idéntica a `Spec 001`.
- **CA-4 (`SINR` Co-Canal en `mW` y Aislamiento por Operador / Banda)**:
  - Con 1 única celda activa ($\mathbf{I}_{\text{mW}} = 0$), $\mathbf{SINR}_{\text{dB}} == \mathbf{RSRP}_{\text{dBm}} - N_{\text{RE (dBm)}}$ al decimal en todos los píxeles.
  - En el borde equidistante entre 2 celdas idénticas co-canal de la misma red con carga $\eta = 1.0$ ($\mathbf{S}_1 = \mathbf{S}_2 \gg N_{\text{RE, mW}}$), la relación $\text{SINR}$ cae exactamente a $\approx 0.0\text{ dB}$ (y con 3 celdas equidistantes idénticas en el centro de un sitio trisectorial, cae a $-10\log_{10}(2) \approx -3.0103\text{ dB}$).
  - Las celdas de otro operador (`Red B` vs `Red A`) o de otra banda (`n28` vs `n78`) **no se suman** a la interferencia co-canal $\mathbf{I}_{\text{mW}}$ de la capa evaluada.
- **CA-5 (Terreno 3D `MDT05` y Frontera `EPSG:25830`)**:
  - Elevar el terreno de un píxel en `ScenarioGrid.with_terrain(...)` hasta quedar por encima de la antena transmisora ($Z_{\text{RX}} > z_{\text{TX}}$) invierte el ángulo cenital a $\Theta_{\text{GCS}} < 90^\circ$ (apuntando hacia arriba del horizonte) y modifica la ganancia de un panel con *downtilt* y la distancia $D_{3\text{D}}$.
  - `wgs84_to_utm30` y `utm30_to_wgs84` son biyectivas (error de ida y vuelta `< 1 mm` en el entorno de Jaén: `lon=-3.7903, lat=37.7692` $\leftrightarrow x \approx 430\,380\text{ m}, y \approx 4\,180\,400\text{ m}$).
  - `sample_grid_terrain` lee un GeoTIFF en `EPSG:25830` y devuelve un `ScenarioGrid` con `terrain_z_m` de dimensiones $(N_y, N_x)$.
- **CA-6 (Ingesta GIS y Escenario `data/cities/jaen.yaml`)**:
  - El pipeline de fusión agrupa celdas OpenCelliD (`MCC=214`), hace *snap* a mástiles OSM cercanos (`<= 75 m`), separa operadores en `Red A`, `Red B` y `Red C` con sus bandas CNAF (`n28`, `n78`) y etiqueta cada sitio con `source: "estimated"` (o `"synthetic"` si es relleno).
  - `data/cities/jaen.yaml` existe en el repositorio con los emplazamientos procesados de Jaén, carga sin red ni API key mediante `load_city_scenario("data/cities/jaen.yaml")`, y permite ejecutar `compute_scenario_coverage` produciendo matrices válidas de `serving_rsrp_dbm` y `sinr_db` para cualquiera de las 3 redes.
- **CA-7 (Invariantes Físicos con `Hypothesis`)**:
  - Propiedades verificadas automáticamente: (1) monotonía decreciente de `SINR` al aumentar el factor de carga interferente $\eta \in [0, 1]$ o al encender celdas co-canal adicionales, (2) cota superior física $\mathbf{SINR}_{\text{dB}} \le \mathbf{SNR}_{\text{dB}} = \mathbf{RSRP}_{\text{dBm}} - N_{\text{RE (dBm)}}$ en todo píxel, y (3) invariancia de ida y vuelta en las proyecciones `EPSG:4326 <-> EPSG:25830` dentro del huso 30N.

---

## 5. Seams Públicos bajo Prueba (Skill `tdd`)

| Seam Público | Qué atrapa (Catches) | Qué no cubre por sí solo (Misses) |
|---|---|---|
| **Seam 1**: `ran_city.domain.grid` (`ScenarioGrid.with_terrain`, `terrain_z_m` en `geometry_from_tx`) | Dimensiones inválidas de relieve, `NaN`s y errores de signo en $\Delta Z$, $D_{3\text{D}}$ y cenital $\Theta_{\text{GCS}}$ sobre terreno con desnivel. | Lectura de archivos GeoTIFF desde disco (`rasterio`). |
| **Seam 2**: `ran_city.radio.tr38901` (`shadow_fading_std_db`, `decorrelation_distance_m`, `sample_shadow_fading_map`, `compute_propagation_matrix(..., include_shadow_fading=True)`) | Desviaciones respecto a `Table 7.4.1-1` y `Table 7.5-6`, pérdida de varianza tras el suavizado espacial 2D o falta de reproducibilidad por semilla. | Impacto del desvanecimiento en la selección de mejor servidor y `SINR`. |
| **Seam 3**: `ran_city.radio.coverage` (`thermal_noise_dbm`, `re_thermal_noise_dbm`, `compute_scenario_coverage` con `sinr_db`, `interference_mw`, filtro `network_alias`/`n_band` y `cell_load_factor`) | Error clásico de usar ancho de banda de canal en vez de `1 RE` para el ruido frente a `RSRP`, sumas ilegales en `dBm` y contaminación de interferencia entre operadores o bandas distintas. | Ingesta de datos externos de Jaén. |
| **Seam 4**: `ran_city.geo.crs` & `ran_city.geo.terrain` (`wgs84_to_utm30`, `utm30_to_wgs84`, `sample_points_elevation`, `sample_grid_terrain`) | Inversiones de ejes `lon/lat` vs `x/y`, errores de reproyección `EPSG:4326 <-> EPSG:25830` y desalineación de filas/columnas al muestrear un GeoTIFF `MDT05`. | Modelos de propagación y `SINR`. |
| **Seam 5**: `ran_city.data_sources.jaen` & `ran_city.data_sources.city_loader` (`cluster_opencellid_and_snap_osm`, `load_city_scenario("data/cities/jaen.yaml")`) | Agrupación defectuosa de celdas OpenCelliD, fallo en el *snap* a mástiles OSM, ausencia de alias `Red A/B/C` o de trazabilidad `source`, e incompatibilidad del YAML generado con `compute_scenario_coverage`. | Renderizado visual en navegador (pospuesto a `Spec 003`). |
