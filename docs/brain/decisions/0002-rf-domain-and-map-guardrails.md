# ADR 0002: Modelo de Producto, Guardarrailes RF y Arquitectura de Mapas

- **Estado**: Aceptado
- **Fecha**: 2026-10-31
- **Decisiones Relacionadas**: [ADR 0001](0001-initial-architecture.md)

## 1. Contexto
Al aterrizar la vision de `RAN-city` sobre Jaen y contrastar el ecosistema abierto de simulacion radio y mapas web, era necesario resolver:
1. Como articular el mapa urbano con temas 5G que ocurren en escalas de milisegundos o protocolos.
2. Que fuentes abiertas de emplazamientos en Espana son legales y como tratar multiples operadores sin errores fisicos en `SINR`.
3. Como renderizar rejillas de cobertura fluidas en el navegador manteniendo compatibilidad con un modo estatico de portfolio y evitando errores tipicos de unidades/angulos al trabajar con agentes de IA.

## 2. Decision
1. **Metafora "Zoom de Escala + Sandbox What-If"**: El mapa de Jaen actua como vista raiz (`km`) sobre una red base estimada reproducible, permitiendo modificaciones *What-If* (con *reset*) e inspectores con explicacion 3GPP integrada en escalas de Antena (`°`), Celda PHY (`ms`/`RB`), UE/Movilidad (`eventos`) y Red (`KPIs`).
2. **Fuentes Abiertas y Alias de Operador (`Red A / B / C`)**:
   - Se descarta *Infoantenas* como fuente automatizada al carecer de API/WFS de reutilizacion abierta.
   - Se adopta **OpenCelliD (`MCC=214`, CC BY-SA 4.0)** cruzado con mastiles **OSM (ODbL)** para emplazamientos `estimated`, completando huecos con nodos `synthetic`.
   - Las celdas importadas se filtran por `MNC` bajo alias neutros (`Red A`, `Red B`, `Red C`) asignados a bloques reales del **CNAF**, calculando `SINR` co-canal unicamente dentro de la red activa seleccionada.
3. **Frontera `EPSG:25830` y Cobertura `NumPy -> PNG -> deck.gl BitmapLayer`**:
   - Todo calculo espacial/RF interno usa coordenadas proyectadas metricas **`EPSG:25830`**; `EPSG:4326` queda restringido a la frontera I/O.
   - Las manchas de cobertura se calculan vectorizadas en `NumPy` y se entregan como rasters ligeros `PNG` + *bounding box* sobre **MapLibre GL JS** (`OpenFreeMap` / `PMTiles`) con `@deck.gl/maplibre` (`BitmapLayer`, `interleaved: true`). Se prohiben rejillas masivas en GeoJSON.
4. **Escudo de Tipos RF y Verificacion con `Hypothesis`**:
   - El dominio encapsula `Dbm`/`Db`/`LinearMw`, `AzimuthDeg` (Norte-horario) y `ZenithDeg` (3GPP TR 38.901 `90° = horizonte`).
   - La suite `pytest` combina casos de referencia 3GPP con *Property-Based Testing* (`hypothesis`) sobre invariantes fisicos; librerias externas (`py3gppchannels`, `pycraf`, `py3gpp`) quedan limitadas a oraculos opcionales de contraste fuera del nucleo.

## 3. Consecuencias
- El mismo contrato de salida alimenta FastAPI en vivo y los snapshots precalculados del portfolio estatico.
- Se eliminan de raiz los fallos de rendimiento en el navegador y las confusiones de signos/unidades entre agentes y modulos.
