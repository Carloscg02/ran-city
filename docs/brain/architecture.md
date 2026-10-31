# Arquitectura de `RAN-city`

## 1. Estilo Arquitectonico
Arquitectura Hexagonal (Puertos y Adaptadores) en Monorepo (`backend/` + `frontend/` + `data/`):
- **Dominio y Fisica Pura (`backend/ran_city/{domain,antenna,radio,air_interface,protocols,mobility,kpis}`)**: Python 3 estricto + `NumPy`/`SciPy` + `Pydantic`. Cero dependencias de HTTP, base de datos, ficheros o frameworks web; importable directamente desde tests y notebooks.
- **Puertos y Seams Publicos**: Contratos tipados para proveer emplazamientos (`estimated` / `synthetic`), modelos digitales del terreno (MDT) y escenarios.
- **Adaptadores de Salida / Datos (`backend/ran_city/{geo,data_sources}`)**: Ingesta reproducible de OpenCelliD (`MCC=214` separado por alias neutros `Red A/B/C` sobre bloques CNAF), mastiles OSM, edificios (Overture Maps / EUBUCCO / Catastro INSPIRE) y relieve CNIG MDT05 (COG), mas exportador estatico de escenarios para portfolio.
- **Adaptadores de Entrada (`backend/ran_city/api` + `frontend/`)**: Capa fina FastAPI (OpenAPI tipado) y visor ligero React + TypeScript + MapLibre GL JS + `@deck.gl/maplibre`. **Prohibido duplicar formulas o logica 5G en TypeScript.**

---

## 2. Verification Commands
Comandos oficiales de verificacion ejecutados por el subagente constructor en cada ciclo:

- **Unit & Integration Tests (In-Loop TDD)**: `backend/.venv/bin/pytest backend/tests`
  Ejecutado en cada iteracion red-green-refactor sobre los seams publicos (incluyendo tests de valores de referencia 3GPP y propiedades fisicas con `hypothesis`).
- **Static / Lint Gate**: `backend/.venv/bin/ruff check backend`
  Ejecutado como barrera de calidad estatica y estilo.
- **E2E / Browser UI Tests (Optional)**: `N/A`
  Ejecutado al completar features que toquen interfaz de usuario o flujos end-to-end completos (se activara con Playwright + `ariaSnapshot` via *Just-In-Time UI Gate* en la primera spec con UI).

---

## 3. Guardarrailes Cientificos, RF y Geoespaciales (Invariantes Duras)

1. **Escudo de Tipos y Convenciones RF (Anti-Alucinacion)**:
   - **Potencias**: Separar explicitamente tipos logaritmicos (`Dbm`, `Db`) y lineales (`LinearMw`). Toda suma o promedio de potencia/ruido/interferencia (`SINR`, recepcion multicelda) pasa obligatoriamente por milivatios lineales (`mW`).
   - **Azimut**: En dominio radio/GIS, `AzimuthDeg` usa convencion brujula (`0° = Norte`, sentido horario, `90° = Este`). La conversion a angulo matematico `atan2` (`0 rad = Este`, antihorario) queda encapsulada en un unico helper testeado.
   - **Angulo Cenital 3GPP (`ZenithDeg`)**: En 3GPP TR 38.901 sec. 7.1, el horizonte es `θ = 90°` y apuntar hacia el suelo (*downtilt*) implica `θ > 90°`. Nunca mezclar con elevacion (`0° = horizonte`) sin conversion explicita.
2. **Frontera Estricta de Coordenadas (CRS)**:
   - Todo calculo metrico 2D/3D de propagacion, distancias y perfiles de terreno en Espana peninsular opera en **`EPSG:25830` (ETRS89 / UTM zona 30N, metros)**.
   - La proyeccion **`EPSG:4326` (`[lon, lat]`)** se utiliza exclusivamente en las fronteras de importacion y de salida HTTP/GeoJSON/UI.
3. **Transporte WebGL de Cobertura (Cero GeoJSON Masivos)**:
   - Prohibido serializar rejillas de cobertura como decenas de miles de poligonos GeoJSON.
   - Las capas de rejilla (`RSRP`, `SINR`, mejor servidor) se evaluan vectorizadas en `NumPy` y se sirven como rasters ligeros (`PNG` RGBA + *bounding box* WGS84) renderizados en GPU con `deck.gl BitmapLayer` (`interleaved: true` sobre MapLibre + `OpenFreeMap` / `PMTiles`). Este mismo formato alimenta tanto el modo FastAPI vivo como el snapshot estatico de portfolio.
4. **Doble Validacion Fisica (Tablas 3GPP + `Hypothesis`)**:
   - Cada formula cita en su docstring la especificacion publica exacta (ej. `3GPP TR 38.901 v17.1.0, Table 7.3-1`).
   - Los tests combinan **casos puntuales calculados a mano / especificacion** con **Property-Based Testing (`hypothesis`)** verificando monotonia, cotas fisicas en dB, invariancia rotacional y degradacion monotona ante interferencia.
   - Librerias externas (`py3gppchannels`, `pycraf`, `py3gpp`) solo pueden usarse como *oraculos de contraste* en tests/estudio, nunca como caja negra en el nucleo de dominio.

---

## 4. Reparto de Trabajo Humano / Agente (Modo Aprendizaje)
- **El agente asume**: andamiaje, configuracion, pipelines GIS/datos, boilerplate FastAPI, integracion MapLibre/deck.gl, refactors e infraestructura de tests.
- **El humano lidera/valida el dominio 5G**: antes de implementar una formula o procedimiento 3GPP, el agente presenta el modelo fisico, las fuentes publicas y el contrato del seam para que el usuario lo implemente o revise linea a linea.
- **Trazabilidad de origen de datos**: toda entidad espacial o de red expone `source: "real" | "estimated" | "synthetic"`.
