---
source: Asignatura Planificación y Optimización de Redes Celulares
topic: Tema 2 - Propagación, Mallado y Matrices
impacts: [domain, antenna, radio, geo]
status: active
---

# Base de Conocimiento: Propagación y Mallado (Tema 2 - Planificación)

Este documento define las reglas de negocio estrictas para el cálculo de cobertura en la simulación de RAN-City, basadas en el temario académico de planificación y optimización de redes celulares. No se debe usar el modelo de propagación en espacio libre (FSPL) como cálculo final de cobertura.

## 1. Modelos de Propagación
El cálculo de pérdidas de propagación debe realizarse utilizando **modelos semideterministas**, específicamente el modelo **Walfisch-Ikegami (W-I)** (o aproximaciones de trazado de rayos).
La configuración del modelo debe contemplar los siguientes parámetros obligatorios:
*   Tipo de celda (macro, micro, pico).
*   Altura de la antena de la Estación Base (BS).
*   Frecuencia de operación.
*   Ángulos de inclinación (Tilt mecánico y eléctrico).

## 2. Reglas de Mallado de Escenario (Grid Resolution)
La evaluación de la cobertura no se hace punto a punto bajo demanda, sino calculando matrices de propagación sobre un escenario mallado. La resolución espacial del grid (`resolution_m`) debe ser adaptativa según el entorno geográfico:
*   **Entorno Denso:** Resolución de **5 metros**.
*   **Entorno Urbano:** Resolución de **12 metros**.
*   **Entorno Rural:** Resolución de **50 metros**.

## 3. Matrices y Calibración
*   **Cálculo matricial:** El sistema debe generar matrices de propagación que contengan las pérdidas desde cada estación base a cada punto (usuario) del escenario mallado.
*   **Calibración (Fase futura):** La arquitectura debe prever el ajuste de las constantes del modelo (W-I) comparándolas con medidas reales geolocalizadas (simulando datos de *Drive Test*).

---

> [!NOTE]
> **Acuerdo de Adopción en `RAN-city` (5G NR, 2026-10-31)**:
> Dado que COST 231 Walfisch-Ikegami está restringido originalmente a `< 2 GHz` (`800–2000 MHz`) y en los apuntes figura como ejemplo de modelo semideterminista, se adopta **3GPP TR 38.901 (`UMa` para macroceldas y `UMi - Street Canyon` para micro/picoceldas, `0.5–100 GHz`)** evaluado matricialmente sobre `ScenarioGrid` de resolución fija por zona (`5 m` Denso, `12 m` Urbano, `50 m` Rural), con estado `LOS/NLOS` probabilístico por distancia (sustituible más adelante por máscara geométrica de edificios reales del Catastro) y parámetros de calibración desacoplados para futuro ajuste con *Drive Test*.
