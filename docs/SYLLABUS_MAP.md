# Radar de Seguimiento del Temario 5G RAN (`T1`–`T9`)

> **Propósito**: Mantener visibilidad total sobre los 9 bloques de formación en 5G RAN mientras priorizamos en `RAN-city` un **hilo conductor coherente** (*Antena → Cobertura → Celda NR → UE en ruta → KPIs*). Ningún tema se pierde: lo que no entra en el hilo inicial queda inventariado aquí para futuras iteraciones o laboratorios específicos.

**Leyenda de estado**:
- `[ ]` Pendiente
- `[~]` En estudio / especificación activa
- `[x]` Implementado y validado con tests + guía en `guides/`

**Leyenda de vía en `RAN-city`**:
- **Hilo Principal**: Forma parte del núcleo *Zoom de Escala* sobre Jaén (`Fase 1–5`).
- **Extensión / Lab**: Se incorporará después del hilo principal cuando aporte valor real al conjunto.

---

## Resumen Ejecutivo por Bloques

| Bloque | Título | Vía Inicial | Inspector / Módulo Objetivo | Progreso |
|---|---|---|---|---|
| **T4** | Antenna Systems | **Hilo Principal (Arranque)** | Inspector Antena (`M1`) + Cobertura (`M2`) | `2 / 4` |
| **T1** | Air Interface | **Hilo Principal** | Link Budget (`M2`) + Inspector Celda PHY (`M3`) | `2.0 / 10` |
| **T2** | RAN Protocol & Procedures | **Hilo Principal (Movilidad/RRC) + Lab** | UE en Ruta (`M5`) + Inspector Protocolos (`M4`) | `0 / 8` |
| **T7** | Multi-layer Coordination & Load Balancing | **Hilo Principal** | Multicapa `n28`/`n78` y Movilidad (`M5`) | `0 / 4` |
| **T3** | NR KPIs | **Hilo Principal** | Inspector Operación y KPIs (`M6`) | `0 / 7` |
| **T5** | Voice over NR (VoNR) | Extensión / Lab contextual | Escenarios de llamada en Inspector Protocolos (`M4+`) | `0 / 5` |
| **T6** | Network Slicing | Extensión / Lab | Particionado de PRBs y SLA por slice (`M7`) | `0 / 5` |
| **T8** | Fixed Wireless Access (FWA) | Extensión sobre Mapa | Planificador FWA y CPEs sobre edificios (`M8`) | `0 / 4` |
| **T9** | NR High-Band (mmWave) RF Initial Tuning | Extensión sobre Mapa | Banda `n258` (26 GHz), bloqueo y tuning (`M9`) | `0 / 4` |

---

## Detalle Punto por Punto

### T4. Antenna Systems *(Punto de arranque junto a T1 base)*
- [x] **Fundamentos**: ganancia, directividad, *beamwidth*, patrón de radiación (3GPP TR 38.901), lóbulos, polarización, VSWR, *front-to-back* — *(Completado en Python: `Spec 001`, pendiente vista interactiva en `M1`)*
- [x] **Tipos de tilt**: mecánico, eléctrico y digital/de haz, e impacto directo en cobertura e interferencia — *(Completado en Python: `Spec 001`)*
- [ ] **Massive MIMO**: SU/MU-MIMO, capas, beamforming analógico/digital/híbrido, configuraciones `TxRx`, CSI vs reciprocidad, haces `SSB` vs tráfico — *(Hilo Principal: `M1` evolución)*
- [ ] **AAS avanzado**: planificación y diseño RF con AAS (cobertura vs capacidad, *link budget*) — *(Hilo Principal: `M1` + `M2`)*

### T1. Air Interface
- [x] **Espectro (base)**: FR1 / FR2, bandas NR españolas (`n28`, `n78`, `n258`), anchos de banda — *(Completado base en `Spec 001`; CA/DC/DSS en `M3+`)*
- [~] **Rendimiento y Link Budget (base)**: potencia recibida (`RSRP` por `RE`, `Best Server`), ruido térmico ($k_B T_0 B F$), *Shadow Fading* 2D correlado y `SINR` co-canal en `mW` completados en `Spec 001` y `Spec 002`; pendiente cadena `SINR -> CQI/MCS -> Throughput` y eficiencia espectral en `M3` — *(Hilo Principal: `Spec 002` + `M3`)*
- [ ] **Numerología**: *subcarrier spacing* (`15/30/60/120 kHz`), slots, símbolos, mini-slots, *resource grid*, `RE`, `RB` — *(Hilo Principal: `M3`)*
- [ ] **Duplexado**: FDD vs TDD, patrones TDD, *slot formats*, SUL *(ampliación)* — *(Hilo Principal: `M3`)*
- [ ] **Modulación y adaptación de enlace**: `QPSK` → `256QAM`, tablas `MCS`, `CQI`, `BLER` objetivo — *(Hilo Principal: `M3`)*
- [ ] **Estructura de canales**: canales lógicos, de transporte y físicos (`PDSCH`, `PDCCH`, `PUSCH`, `PUCCH`, `PRACH`, `PBCH`), `SSB`, señales de referencia (`DMRS`, `CSI-RS`, `SRS`, `PT-RS`) — *(Hilo Principal: `M3`)*
- [ ] **Asignación de recursos**: *Bandwidth Parts (BWP)*, *scheduling* DL/UL, *grants* dinámicos y configurados — *(Extensión `M3+`)*
- [ ] **Carrier Aggregation, Dual Connectivity y DSS** *(ampliación)* — *(Extensión `M3+` / `M5`)*
- [ ] **Mapeo de QoS**: `5QI`, *QoS flows*, mapeo `QoS flow → DRB` — *(Extensión: conecta con `T5`/`T6`)*
- [ ] **Gestión de interferencias y Evolución Rel. 15 → 18**: inter-celda, *cross-link* TDD, *remote interference* / *ducting*, 5G-Advanced — *(Extensión teórica / `M2+`)*

### T2. RAN Protocol & Procedures
- [ ] **Movilidad**: reselección, handover intra/inter-frecuencia, `Xn`/`NG`, eventos `A1–A6` / `B1–B2`, *Conditional HO* *(ampliación)* — *(Hilo Principal: `M5`)*
- [ ] **NSA EN-DC**: *anchor* LTE, `SgNB` addition/release, *split bearer* *(ampliación)* — *(Hilo Principal: `M5`)*
- [ ] **Arquitectura RAN**: `gNB`, *split* `CU/DU`, interfaces `NG / Xn / F1 / E1`, separación `CP/UP` *(ampliación)* — *(Inspector Protocolos: `M4`)*
- [ ] **Pila de protocolos**: `SDAP`, `PDCP`, `RLC` (TM/UM/AM), `MAC` (HARQ, BSR, DRX), `PHY`; `RRC` (`IDLE` / `INACTIVE` / `CONNECTED`) — *(Inspector Protocolos: `M4`)*
- [ ] **Acceso inicial**: *cell search*, `SSB`, `MIB/SIBs`, *Random Access* (4-step / 2-step), `RRC Setup` — *(Inspector Protocolos: `M4`)*
- [ ] **Registro y sesión**: *Registration* con 5GC, seguridad, `PDU Session` — *(Inspector Protocolos: `M4`)*
- [ ] **Scheduling y transmisión extremo a extremo** — *(Extensión `M4+`)*
- [ ] **Beam management y beam failure recovery** *(ampliación)* — *(Extensión: puente `T4` ↔ `T2`)*

### T7. Multi-layer Coordination & Load Balancing
- [ ] **SA multicapa**: prioridades de reselección, estrategia de handover, coordinación *low/mid/high band* (`n28` + `n78`) — *(Hilo Principal: `M5`)*
- [ ] **NSA gestión de capa ancla**: medidas `B1`, `SCG` addition/release, *Upper Layer Indication* — *(Hilo Principal: `M5`)*
- [ ] **Interworking 5G ↔ LTE**: HO inter-RAT, *release with redirect*, *EPS Fallback*, `N26` — *(Extensión `M5+`, conecta con `T5`)*
- [ ] **Load balancing y traffic steering** — *(Extensión `M5+` / `M6`)*

### T3. NR KPIs
- [ ] **Performance Management**: contadores, eventos, periodos de medida (`ROP`), fórmulas y agregación (3GPP TS 28.552) — *(Hilo Principal: `M6`)*
- [ ] **Accesibilidad**: `RRC Setup SR`, `NG signaling SR`, `PDU Session / QoS Flow setup SR`, `EN-DC SCG setup SR` — *(Hilo Principal: `M6`)*
- [ ] **Retenibilidad**: caídas anormales, liberaciones anormales de `SCG` — *(Hilo Principal: `M6`)*
- [ ] **Integridad**: throughput DL/UL, latencia, `BLER`, volumen — *(Hilo Principal: `M6`)*
- [ ] **Movilidad**: `HO SR` intra/inter-frecuencia, inter-RAT, *PSCell change* — *(Hilo Principal: `M6`)*
- [ ] **Disponibilidad y utilización**: disponibilidad de celda, utilización de `PRB`, usuarios activos, carga de `PDCCH` — *(Hilo Principal: `M6`)*
- [ ] **Troubleshooting a partir de KPIs** *(inyección de fallos What-If: sitio caído, interferencia, mal tilt)* — *(Hilo Principal: `M6`)*

### T5. Voice over NR *(En recámara — Extensión sobre Inspector de Protocolos y Movilidad)*
- [ ] Evolución: `CSFB → VoLTE → EPS Fallback → VoNR`
- [ ] Arquitectura: `IMS` + `5GC` (`AMF`, `SMF`, `UPF`, `PCF`); `5QI 1` y `5QI 5`
- [ ] Call flows: registro IMS, llamada MO/MT, *EPS Fallback*
- [ ] Procedimientos RAN: *QoS flow* y `DRB` de voz, `RLC UM`, `ROHC`, `DRX`, movilidad en llamada
- [ ] Features RAN para priorizar voz, diferencias VoLTE vs VoNR y KPIs de voz

### T6. Network Slicing *(En recámara — Extensión sobre Celda y KPIs)*
- [ ] Concepto y casos de uso (`eMBB`, `URLLC`, `mIoT`)
- [ ] `S-NSSAI` (`SST + SD`), `NSSAI` solicitada/permitida
- [ ] Slicing en `5GC`: `NSSF`, selección de funciones por slice
- [ ] Visión extremo a extremo: orquestación, RAN, core, transporte
- [ ] Slicing en RAN: particionado de recursos (`PRB`), priorización y aseguramiento de SLA

### T8. Fixed Wireless Access *(En recámara — Extensión sobre Mapa y Edificios de Jaén/Málaga)*
- [ ] Mercado FWA y comparativa con FTTH, DSL, cable y satélite
- [ ] Segmentos FWA
- [ ] Flujo de análisis de despliegue: demanda por edificio, cobertura, capacidad por celda y *business case*
- [ ] Tipos de CPE: *indoor*, *outdoor*, *window-mounted* (ganancia de antena y pérdidas de penetración)

### T9. NR High-Band (mmWave) RF Initial Tuning *(En recámara — Candidato con `Sionna RT` en zona densa)*
- [ ] Propagación en mmWave (`26 GHz / n258`): penetración, follaje, bloqueo por edificios
- [ ] Objetivos, principios y metodología del *initial tuning*
- [ ] Parámetros optimizados: tilt, azimut, barrido de haces, potencia
- [ ] Criterios de aceptación y KPIs del tuning
