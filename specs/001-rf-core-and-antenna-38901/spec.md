# Spec 001: Mallado por Zona, Antena y Matrices de Propagación 3GPP TR 38.901 (`001-rf-core-and-antenna-38901`)

- **Estado**: Aprobado
- **Modalidad de Ejecución Confirmada**: **Modo 2 — Co-implementación guiada** (ciclos verticales `RED -> GREEN` explicando y revisando contigo cada bloque matemático línea a línea)
- **Fuentes Curriculares**:
  - Temario 5G RAN: `T4` (*Antenna Systems*) + `T1 base` (*Air Interface*: bandas NR, potencia por `RE` y `SS-RSRP`)
  - Asignatura Planificación de Redes: [`docs/course-notes/001_propagacion_mallado_T2.md`](../../docs/course-notes/001_propagacion_mallado_T2.md) (modelo semideterminista sin `FSPL` como cobertura final, tipos `macro`/`micro`/`pico`, tilts mecánico y eléctrico, mallado `5 m / 12 m / 50 m`, matrices de propagación BS → malla y soporte arquitectónico para calibración con *Drive Test*)
- **Carril**: `SDD` — Fase 1 (`spec.md`)

---

## 1. Contexto y Propósito

Esta primera especificación construye el motor matemático matricial de `RAN-city` en Python puro (`NumPy` + `Pydantic`), replicando la arquitectura interna de un planificador celular real (*estilo Atoll*) adaptada nativamente a frecuencias 5G NR (`0.5–100 GHz`):

1. Un **escenario geográfico en coordenadas métricas (`EPSG:25830`)** se discretiza en una matriz regular 2D (`ScenarioGrid`) cuya resolución espacial depende de la categoría de la zona (**`5 m` Denso**, **`12 m` Urbano**, **`50 m` Rural**).
2. Para cada celda (`macro` → **UMa**; `micro` / `pico` → **UMi - Street Canyon**), el motor calcula de forma vectorizada y **desacoplada**:
   - **Matriz de Propagación Isótropa ($\mathbf{L}_{\text{prop}}$)**: pérdidas de trayecto **3GPP TR 38.901** hacia cada píxel de la malla, con decisión de estado `LOS / NLOS` probabilística por distancia (semilla reproducible, y preparada para aceptar máscaras geométricas reales de edificios del Catastro en `Spec 002+`) más coeficientes de calibración desacoplados para futuro ajuste con *Drive Test*.
   - **Matriz Directiva de Antena ($\mathbf{G}_{\text{ant}}$)**: ganancia 3D del panel **3GPP TR 38.901** ($N_V \times N_H$) hacia cada píxel aplicando azimut, **tilt mecánico** y **tilt eléctrico**.
3. Al combinar ambas matrices con la potencia por *Resource Element* ($P_{\text{TX,RE}}$), obtenemos las matrices de **pérdida efectiva**, **`RSRP` por celda**, **`Serving RSRP`** y **`Best Server`** sobre toda la zona, permitiendo recalcular cambios de *tilt* o potencia al instante sin recomputar $\mathbf{L}_{\text{prop}}$.

---

## 2. Formulación Matemática Exacta y Fuentes Públicas

### 2.1 Unidades, Geometría Métrica y Mallado (`ScenarioGrid`)
- **Potencias**: conversión estricta $P_{\text{mW}} = 10^{P_{\text{dBm}}/10}$ y $P_{\text{dBm}} = 10\log_{10}(P_{\text{mW}})$. Prohibida cualquier suma de potencias en `dBm` (tipado separado `Dbm`, `Db`, `LinearMw`).
- **Convención angular**:
  - `AzimuthDeg`: brújula telecom (`0° = Norte`, sentido horario: `90° = Este`, `180° = Sur`).
  - `ZenithDeg` ($\theta \in [0^\circ, 180^\circ]$): ángulo cenital 3GPP (`0° = cenit`, **`90° = horizonte`**, `180° = nadir/suelo`).
- **Resoluciones normativas por entorno** ([`001_propagacion_mallado_T2.md`](../../docs/course-notes/001_propagacion_mallado_T2.md)):
  - `EnvironmentType.DENSE_URBAN` $\rightarrow \Delta_{\text{grid}} = 5.0\text{ m}$
  - `EnvironmentType.URBAN` $\rightarrow \Delta_{\text{grid}} = 12.0\text{ m}$
  - `EnvironmentType.RURAL` $\rightarrow \Delta_{\text{grid}} = 50.0\text{ m}$
- Para una estación en $(x_{\text{BS}}, y_{\text{BS}}, z_{\text{ground}} + h_{\text{BS}})$ y receptores a altura $h_{\text{UT}}$ sobre el plano de la malla $(X, Y)$, se obtienen matrices 2D $(N_y, N_x)$ de distancias $D_{2\text{D}}$, $D_{3\text{D}} = \max\big(1.0\text{ m}, \sqrt{D_{2\text{D}}^2 + (h_{\text{BS}} - h_{\text{UT}})^2}\big)$ y ángulos esféricos globales $(\Theta_{\text{GCS}}, \Phi_{\text{GCS}})$.

### 2.2 Antena Directiva y Tilts — *3GPP TR 38.901 v17.1.0 Clauses 7.1, 7.3 (Table 7.3-1) & ITU-R M.2101-0 Sec. 5*
1. **Elemento individual en coordenadas locales `LCS` $(\theta', \phi')$** ($G_{E,\max} = 8\text{ dBi}$, $\theta_{3\text{dB}} = \phi_{3\text{dB}} = 65^\circ$, $\text{SLA}_V = A_{\max} = 30\text{ dB}$):
   $$A_{E,V}(\theta') = -\min\left(12\left(\frac{\theta' - 90^\circ}{\theta_{3\text{dB}}}\right)^2, \; \text{SLA}_V\right), \qquad A_{E,H}(\phi') = -\min\left(12\left(\frac{\phi'}{\phi_{3\text{dB}}}\right)^2, \; A_{\max}\right)$$
   $$A_E(\theta', \phi') = G_{E,\max} - \min\left(-\left[A_{E,V}(\theta') + A_{E,H}(\phi')\right], \; A_{\max}\right)$$
2. **Tilt Mecánico ($\beta > 0$ inclina hacia el suelo) — Rotación `GCS → LCS` (*TR 38.901 Eq. 7.1-7 y 7.1-8*, *slant* $\gamma = 0$)**:
   $$\cos\theta' = \cos\beta\cos\theta + \sin\beta\sin\theta\cos\phi, \qquad \phi' = \operatorname{atan2}\left(\sin\theta\sin\phi, \; \cos\beta\sin\theta\cos\phi - \sin\beta\cos\theta\right)$$
3. **Array Plano `UPA` ($N_V \times N_H$) y Tilt Eléctrico ($\theta_{\text{etilt}}$)**:
   Con espaciados $d_V/\lambda, d_H/\lambda$ (por defecto $0.5$) y pesos unitarios $|w_{m,n}| = 1/\sqrt{N_V N_H}$ apuntando a $(\theta_{\text{steer}} = 90^\circ + \theta_{\text{etilt}}, \; \phi_{\text{escan}})$:
   $$G_{\text{ant}}(\theta', \phi') = A_E(\theta', \phi') + 10\log_{10}\left(\left|\sum_{m=0}^{N_V-1}\sum_{n=0}^{N_H-1} w_{m,n} \, v_{m,n}(\theta', \phi')\right|^2\right)$$

### 2.3 Probabilidad de Vista Directa (`LOS`) — *3GPP TR 38.901 v17.1.0, Table 7.4.2-1*
Evaluada matricialmente sobre $D_{2\text{D}}$ (en metros):
- **`UMi - Street Canyon` (asignado a `CellType.MICRO` y `CellType.PICO`)**:
  $$\text{Pr}_{\text{LOS,UMi}}(d_{2\text{D}}) = \begin{cases} 1.0, & d_{2\text{D}} \le 18\text{ m} \\ \frac{18}{d_{2\text{D}}} + \exp\left(-\frac{d_{2\text{D}}}{36}\right)\left(1 - \frac{18}{d_{2\text{D}}}\right), & d_{2\text{D}} > 18\text{ m} \end{cases}$$
- **`UMa` (asignado a `CellType.MACRO`)**:
  $$\text{Pr}_{\text{LOS,UMa}}(d_{2\text{D}}, h_{\text{UT}}) = \begin{cases} 1.0, & d_{2\text{D}} \le 18\text{ m} \\ \min\left(1.0, \; \left[\frac{18}{d_{2\text{D}}} + \exp\left(-\frac{d_{2\text{D}}}{63}\right)\left(1 - \frac{18}{d_{2\text{D}}}\right)\right] \left[1 + C'(h_{\text{UT}})\frac{5}{4}\left(\frac{d_{2\text{D}}}{100}\right)^3 \exp\left(-\frac{d_{2\text{D}}}{150}\right)\right]\right), & d_{2\text{D}} > 18\text{ m} \end{cases}$$
  donde $C'(h_{\text{UT}}) = 0$ si $h_{\text{UT}} \le 13\text{ m}$, y $\left(\frac{h_{\text{UT}} - 13}{10}\right)^{1.5}$ si $13\text{ m} < h_{\text{UT}} \le 23\text{ m}$.
- **Resolución del estado `LOS / NLOS`**:
  - Si no se inyecta máscara geométrica externa (`los_mask=None`), cada píxel realiza un ensayo de Bernoulli reproducible `U(y, x) < Pr_LOS(y, x)` mediante `np.random.default_rng(seed)`.
  - Si se inyecta `los_mask: np.ndarray[bool]` (para tests deterministas o futura geometría real de edificios del Catastro), el modelo la utiliza directamente sin cambiar las ecuaciones de pérdidas.

### 2.4 Pérdidas de Propagación Semideterministas — *3GPP TR 38.901 v17.1.0, Table 7.4.1-1*
Con $f_c$ en **GHz** ($0.5 \le f_c \le 100$), $d_{2\text{D}}, d_{3\text{D}}$ en **metros**, $c = 299\,792\,458\text{ m/s}$ y distancia de ruptura $d'_{\text{BP}} = \frac{4 \, h'_{\text{BS}} \, h'_{\text{UT}} \, (f_c \cdot 10^9)}{c}$ con alturas efectivas $h'_{\text{BS}} = \max(0.5, h_{\text{BS}} - 1.0)$ y $h'_{\text{UT}} = \max(0.5, h_{\text{UT}} - 1.0)$:

1. **Modelo `UMa` (`macro`)**:
   - **Rama `LOS`**:
     $$\text{PL}_{\text{UMa-LOS}} = \begin{cases} 28.0 + 22\log_{10}(d_{3\text{D}}) + 20\log_{10}(f_c), & d_{2\text{D}} \le d'_{\text{BP}} \\ 28.0 + 40\log_{10}(d_{3\text{D}}) + 20\log_{10}(f_c) - 9\log_{10}\left((d'_{\text{BP}})^2 + (h_{\text{BS}} - h_{\text{UT}})^2\right), & d_{2\text{D}} > d'_{\text{BP}} \end{cases}$$
   - **Rama `NLOS`**:
     $$\text{PL}'_{\text{UMa-NLOS}} = 13.54 + 39.08\log_{10}(d_{3\text{D}}) + 20\log_{10}(f_c) - 0.6(h_{\text{UT}} - 1.5)$$
     $$\text{PL}_{\text{UMa-NLOS}} = \max\left(\text{PL}_{\text{UMa-LOS}}, \; \text{PL}'_{\text{UMa-NLOS}}\right)$$

2. **Modelo `UMi - Street Canyon` (`micro` / `pico`)**:
   - **Rama `LOS`**:
     $$\text{PL}_{\text{UMi-LOS}} = \begin{cases} 32.4 + 21\log_{10}(d_{3\text{D}}) + 20\log_{10}(f_c), & d_{2\text{D}} \le d'_{\text{BP}} \\ 32.4 + 40\log_{10}(d_{3\text{D}}) + 20\log_{10}(f_c) - 9.5\log_{10}\left((d'_{\text{BP}})^2 + (h_{\text{BS}} - h_{\text{UT}})^2\right), & d_{2\text{D}} > d'_{\text{BP}} \end{cases}$$
   - **Rama `NLOS`**:
     $$\text{PL}'_{\text{UMi-NLOS}} = 22.4 + 35.3\log_{10}(d_{3\text{D}}) + 21.3\log_{10}(f_c) - 0.3(h_{\text{UT}} - 1.5)$$
     $$\text{PL}_{\text{UMi-NLOS}} = \max\left(\text{PL}_{\text{UMi-LOS}}, \; \text{PL}'_{\text{UMi-NLOS}}\right)$$

3. **Gancho de Calibración (`CalibrationParams`)**:
   Cada modelo admite un vector inmutable `CalibrationParams(offset_db=0.0, dist_log_delta=0.0, freq_log_delta=0.0)` que suma $\Delta L = \text{offset\_db} + \text{dist\_log\_delta}\cdot\log_{10}(d_{3\text{D}}) + \text{freq\_log\_delta}\cdot\log_{10}(f_c)$ a la matriz $\mathbf{L}_{\text{prop}}$, dejando preparada la regresión futura frente a medidas geolocalizadas de *Drive Test*.

### 2.5 Matrices de Cobertura y `SS-RSRP` por `RE` — *3GPP TS 38.215 Clause 5.1.1*
- Potencia radiada por *Resource Element* (`12 RE` por `RB`, **TS 38.211**):
  $$P_{\text{TX,RE (dBm)}} = P_{\text{TX,total (dBm)}} - 10\log_{10}(12 \cdot N_{\text{RB}})$$
- Matrices por celda $k$ sobre la malla $(N_y, N_x)$:
  $$\mathbf{L}_{\text{eff}, k} = \mathbf{L}_{\text{prop}, k} + L_{\text{TX}, k} + L_{\text{RX}} - \mathbf{G}_{\text{ant}, k}(\beta_k, \theta_{\text{etilt}, k}) - G_{\text{RX}}$$
  $$\mathbf{RSRP}_k = P_{\text{TX,RE}, k} - \mathbf{L}_{\text{eff}, k}$$
- Agregación multicelda del escenario: `serving_rsrp_dbm = np.max(rsrp_stack, axis=0)` y `best_server_idx = np.argmax(rsrp_stack, axis=0)`.

---

## 3. Requerimientos Funcionales y Alcance

### Incluido en `Spec 001`
1. **Entorno y Calidad (`backend/`)**: `pyproject.toml` y `backend/.venv` con `numpy`, `pydantic`, `pytest`, `hypothesis` y `ruff`.
2. **Unidades y Mallado (`ran_city.domain.units`, `ran_city.domain.grid`)**:
   - Tipos `Dbm`, `Db`, `LinearMw`, `AzimuthDeg`, `ZenithDeg`, `Point3D`.
   - `EnvironmentType` (`DENSE_URBAN=5m`, `URBAN=12m`, `RURAL=50m`) y `ScenarioGrid` en `EPSG:25830` capaz de generar coordenadas de malla y tensores geométricos $(D_{2\text{D}}, D_{3\text{D}}, \Theta, \Phi)$ respecto a una estación.
3. **Modelos de Dominio (`ran_city.domain.models`)**:
   - `DataSourceOrigin` (`real` | `estimated` | `synthetic`), `CellType` (`macro` | `micro` | `pico`), `NrBand` (presets `n28`, `n78`, `n258`), `AntennaConfig`, `Cell`, `Sector` y `Site`.
4. **Motor Vectorizado de Antena (`ran_city.antenna.tr38901`)**:
   - Elemento `TR 38.901`, rotación `GCS → LCS` por azimut y tilt mecánico, array `UPA` ($N_V \times N_H$) con tilt/scan eléctrico y cálculo directo de matriz $\mathbf{G}_{\text{ant}}$ sobre un `ScenarioGrid`.
5. **Motor Matricial de Propagación y Cobertura (`ran_city.radio.tr38901`, `ran_city.radio.coverage`)**:
   - Probabilidad `LOS` (`Table 7.4.2-1`), muestreador estocástico reproducible con soporte para `los_mask` explícita, *path loss* `UMa` y `UMi - Street Canyon` (`Table 7.4.1-1`), `CalibrationParams`, matriz $\mathbf{L}_{\text{prop}}$ por celda y cálculo multicelda de matrices $\mathbf{L}_{\text{eff}}$, $\mathbf{RSRP}$, `serving_rsrp_dbm` y `best_server_idx`.

### Fuera de Alcance (pospuesto a `Spec 002+`)
- Polígonos reales de edificios de Catastro/Overture, relieve `MDT05`, *shadow fading* espacialmente correlado, ajuste automático por mínimos cuadrados de *Drive Test*, `SINR` multicapa e interfaz web `FastAPI` + `MapLibre`.

---

## 4. Criterios de Aceptación (CA)

- **CA-1 (Tooling Verde)**: `backend/.venv/bin/pytest backend/tests` y `backend/.venv/bin/ruff check backend` terminan con salida `0`.
- **CA-2 (Mallado por Zona `5m / 12m / 50m` y Geometría)**:
  - `ScenarioGrid.from_bounds(..., env=EnvironmentType.DENSE_URBAN | URBAN | RURAL)` aplica automáticamente `5.0 m`, `12.0 m` y `50.0 m` y genera dimensiones $(N_y, N_x)$ coherentes en metros (`EPSG:25830`).
  - Conversiones `dBm ↔ mW` exactas y orientación brújula verificada (`N=0°`, `E=90°`, `S=180°`, `W=270°`, horizonte $\theta = 90^\circ$).
- **CA-3 (Antena 3GPP TR 38.901 y Diferencia Tilt Mecánico vs. Eléctrico)**:
  - Elemento individual clava `8.0 dBi` en *boresight*, `5.0 dBi` en $\pm 32.5^\circ$ (`-3 dB`) y `-22.0 dBi` en espalda/polos (`A_max = 30 dB`).
  - Panel `8 × 8` suma `+18.0618 dB` (`26.0618 dBi`); se verifica numéricamente el comportamiento distinto en los laterales ($\phi = \pm 90^\circ$) entre tilt mecánico $\beta = 10^\circ$ y tilt eléctrico $\theta_{\text{etilt}} = 10^\circ$.
- **CA-4 (Probabilidad `LOS` y Propagación `TR 38.901` `UMa` / `UMi`)**:
  - Para $d_{2\text{D}} \le 18\text{ m}$, $\text{Pr}_{\text{LOS}} == 1.0$ tanto en `UMa` como en `UMi`; para $d_{2\text{D}} > 18\text{ m}$ decrece monótonamente y coincide con los valores analíticos de `Table 7.4.2-1`.
  - Con misma `seed`, la máscara booleana `LOS/NLOS` es 100% determinista; si se pasa `los_mask` explícita, respeta exactamente dicha máscara.
  - Los valores de $\text{PL}_{\text{UMa}}$ (`macro`, `n78 = 3.5 GHz`, $h_{\text{BS}} = 25\text{ m}$) y $\text{PL}_{\text{UMi}}$ (`micro`/`pico`, $h_{\text{BS}} = 10\text{ m}$) antes y después de $d'_{\text{BP}}$, en `LOS` y `NLOS`, coinciden al decimal con el cálculo manual de `Table 7.4.1-1`, cumpliéndose siempre $\text{PL}_{\text{NLOS}} \ge \text{PL}_{\text{LOS}}$.
- **CA-5 (Desacoplo Matricial, Calibración y Multicelda)**:
  - Modificar `mechanical_tilt_deg`, `electrical_tilt_deg` o `tx_power_dbm` cambia $\mathbf{G}_{\text{ant}}$ y $\mathbf{RSRP}$ sin alterar $\mathbf{L}_{\text{prop}}$.
  - Aplicar un `CalibrationParams(offset_db=+3.5)` incrementa exactamente `+3.5 dB` toda la matriz $\mathbf{L}_{\text{prop}}$ y reduce `-3.5 dB` el $\mathbf{RSRP}$.
  - En un escenario con un `Site` trisectorial (`0° / 120° / 240°`), `best_server_idx` particiona coherentemente el plano en 3 sectores dominantes.
- **CA-6 (Invariantes Físicos con `Hypothesis`)**:
  - Propiedades verificadas sobre cientos de entradas aleatorias: (1) $\text{Pr}_{\text{LOS}} \in [0, 1]$ y monótona decreciente con $d_{2\text{D}}$, (2) $\text{PL}_{\text{NLOS}} \ge \text{PL}_{\text{LOS}}$ en todo el dominio `0.5–100 GHz`, (3) monotonía creciente del *path loss* determinista con la distancia, (4) cota superior física de $\mathbf{G}_{\text{ant}}$, y (5) invariancia rotacional sobre mallas simétricas.

---

## 5. Seams Públicos bajo Prueba (Skill `tdd`)

| Seam Público | Qué atrapa (Catches) | Qué no cubre por sí solo (Misses) |
|---|---|---|
| **Seam 1**: `ran_city.domain.units` & `ran_city.domain.grid` (`Dbm`/`LinearMw`, `ScenarioGrid`) | Errores `dBm ↔ mW`, resoluciones erróneas fuera de `5m/12m/50m` y fallos en matrices $(D_{2\text{D}}, D_{3\text{D}}, \Theta, \Phi)$ o azimut Norte-horario. | Ecuaciones de antena y propagación 3GPP. |
| **Seam 2**: `ran_city.domain.models` (`Site`, `Sector`, `Cell`, `AntennaConfig`, `NrBand`) | Configuraciones físicas ilegales ($f_c \notin [0.5, 100]\text{ GHz}$, $N_V < 1$, ausencia de `CellType` o `source`). | Exactitud matemática del motor RF. |
| **Seam 3**: `ran_city.antenna.tr38901` (`element_gain_dbi`, `compute_antenna_gain_matrix`) | Desviaciones en Table 7.3-1, errores de signo en rotación mecánica `GCS → LCS` y en suma de fases `UPA`. | Pérdidas de propagación y nivel recibido `RSRP`. |
| **Seam 4**: `ran_city.radio.tr38901` (`los_probability`, `compute_propagation_matrix`) | Errores en `Table 7.4.2-1` (`Pr_LOS`), distancia de ruptura $d'_{\text{BP}}$, ramas `UMa`/`UMi` (`LOS`/`NLOS`) y aplicación de `CalibrationParams`. | Orientación directiva del sector y reparto de potencia por `RE`. |
| **Seam 5**: `ran_city.radio.coverage` (`compute_cell_coverage`, `compute_scenario_coverage`) | Integración matricial completa ($\mathbf{L}_{\text{prop}} + \mathbf{G}_{\text{ant}} + P_{\text{TX,RE}} \rightarrow \mathbf{RSRP}$ y `Best Server` trisectorial) y desacoplo ante cambios de tilt. | Obstrucción determinista con edificios reales (futura `Spec 002`). |
