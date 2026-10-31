---
name: project-architect
description: Negociacion de arquitectura de software y diagnostico Greenfield vs Brownfield.
---

# Project Architect Skill

Guia al agente en la negociacion arquitectonica y estructuracion inicial para `RAN-city`.

## 1. Principio Rector: Hexagonal por Defecto pero Adaptable
- Por defecto, propone Arquitectura Hexagonal / Puertos y Adaptadores con separacion estricta entre Dominio e I/O.
- Evalua la naturaleza y tamano real del proyecto. Si una arquitectura en capas (`layered`), MVC (`mvc`) o script modular (`script`) es mas idonea, acuerda el cambio antes de escribir codigo.
- Registra el estilo acordado (`hexagonal`) en `docs/brain/architecture.md`.
- Genera el ADR fundacional en `docs/brain/decisions/0001-initial-architecture.md`.

## 2. Diagnostico Greenfield vs Brownfield y Regla de Granularidad de `modules/`
- Si el proyecto es **Greenfield**: inicializa el cerebro limpio con politicas de testing y carpetas base.
- Si el proyecto es **Brownfield**: inspecciona dependencias, tests existentes y estructura previa sin sobreescribir la logica de negocio.
- **Regla Estricta para `docs/brain/modules/` (Vertical Domain Slices, NUNCA Capas Horizontales)**:
  - **PROHIBIDO** crear fichas de modulos por capas tecnicas horizontales como `domain.md`, `application.md`, `adapters.md`, `controllers.md` o `models.md`. La explicacion de las capas horizontales vive unicamente en `docs/brain/architecture.md`.
  - **OBLIGATORIO**: Agrupa `docs/brain/modules/<capacidad>.md` por **Subsistemas Funcionales o Capacidades de Dominio** (Bounded Contexts / Feature Domains, por ejemplo: `auth-and-users.md`, `tax-calculation-engine.md`, `invoice-ai-extraction.md`, `market-valuation.md`, `property-and-lease-management.md`, `frontend-ui.md`).
  - Cada ficha funcional en `docs/brain/modules/<capacidad>.md` debe mapear el corte vertical completo de esa capacidad:
    1. Que entidades/puertos de dominio usa.
    2. Que casos de uso ejecuta.
    3. Que adaptadores concretos (DB, APIs externas, IA, PDF) y rutas HTTP/UI involucra.
    4. Donde estan sus tests especificos.
- **Consolidacion de Contratos UI y Archivos Legacy en Brownfield**:
  - Si existe un `DESIGN.md` en la raiz del proyecto, sintetiza sus tokens, tipografia y reglas en `docs/brain/design.md` (`<= 80` lineas) durante el onboarding para que el contrato UI quede activo en el Cerebro.
  - Si existen archivos de arneses antiguos (`agents.md` en minusculas, `SDD-WoW.md`, `.agent/`), advierte al usuario y consolida su conocimiento util en el nuevo Cerebro para no dejar dos routers contradictorios (`AGENTS.md` vs `agents.md`).
