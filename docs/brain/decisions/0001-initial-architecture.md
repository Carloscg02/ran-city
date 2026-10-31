# ADR 0001: Eleccion de arquitectura inicial

- **Estado**: Aceptado
- **Fecha**: Inicial
- **Estilo Acordado**: `hexagonal`

## 1. Contexto
Al inicializar `RAN-city` con el objetivo de `Simulador interactivo y laboratorio educativo de redes 5G RAN sobre Jaen (Zoom de escala: Ciudad -> Antena -> Celda PHY -> UE/Movilidad -> KPIs, con red base estimada OpenCelliD/OSM y sandbox What-If)`, se requiere establecer las fronteras arquitectonicas base.

## 2. Decision
Se adopta el estilo `hexagonal` para estructurar el codigo y los seams de prueba.

## 3. Consecuencias
Todo nuevo componente o feature desarrollada en el proyecto debe respetar las directrices registradas en `docs/brain/architecture.md`.
