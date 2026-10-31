---
name: mentor-guide
description: Generador bajo demanda de guias educativas tecnicas (guides/<slug>-GUIDE.md) con doble lente.
---

# Mentor Guide Skill

Define el protocolo para redactar guias didacticas profundas en `guides/` para el proyecto `RAN-city`.

## 1. Disparador
Se activa cuando el usuario solicita una explicacion profunda, un tutorial o cuando se cierra un hito relevante y se requiere transferir conocimiento pedagogico.

## 2. Enfoque de Doble Lente
Cada guia generada en `guides/<slug>-GUIDE.md` debe combinar dos perspectivas:
1. **Lente de Ingenieria de Software**:
   - Principios de diseno, modularidad, patrones de arquitectura limpia y testing riguroso (TDD).
   - Analisis de trade-offs, mantenibilidad y robustez de codigo.
2. **Lente de Dominio Tecnico**:
   - Dominio especifico del proyecto: `5G NR Radio Access Network (3GPP Physical Layer, Antenna Systems TR 38.901, RF Propagation, RAN Protocols & PM KPIs)`.
   - Conceptos teoricos y practicos propios de dicho dominio aplicados en el codigo del repositorio.

## 3. Estructura Didactica
- Introduccion y contextualizacion del problema.
- Fundamentos teoricos (diagramas Mermaid cuando aporten claridad).
- Diseccion del codigo implementado en el repositorio (referenciando archivos y funciones).
- Lecciones aprendidas y buenas practicas recomendadas.
