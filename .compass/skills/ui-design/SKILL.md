---
name: ui-design
description: Gobernanza de diseno UI/Frontend, entrevista guiada, arquetipos con personalidad y reglas duras Anti-Slop.
---

# UI Design Skill: `RAN-city`

Gobernanza de interfaz grafica y diseno para evitar AI Slop y Zombie UI en `RAN-city`.

## 1. Protocolo de Activacion (Just-In-Time UI Gate)
Antes de escribir o modificar codigo de interfaz visual (HTML, CSS, Tailwind, React, Vue, Svelte o componentes), comprobar si existe `docs/brain/design.md` (o `DESIGN.md` en la raiz). Si no existe, detenerse inmediatamente y ejecutar este protocolo antes de programar componentes.

## 2. Camino A — Coherencia en Proyectos con UI Existente (Brownfield UI)
Si el proyecto ya contiene componentes frontend, configuraciones de Tailwind/PostCSS (`tailwind.config.*`), `globals.css`, `components.json` o un `DESIGN.md` previo:
1. Inspeccionar la paleta de colores, tipografia, radios de borde y libreria de componentes existentes.
2. Extraer y formalizar estos acuerdos en `docs/brain/design.md` respetando la direccion visual previa para evitar estilos paralelos inconsistentes.

## 3. Camino B — Entrevista de Diseno desde Cero (Greenfield UI)
Prohibido generar codigo visual por defecto sin antes consensuar la direccion con el desarrollador mediante 3 preguntas breves en el chat:
1. **Proposito y Sensacion**: Que problema resuelve la interfaz y que atmosfera debe transmitir (precision tecnica, calidez editorial, telemetria industrial, o audacia neo-brutalista).
2. **Exploracion Visual Guiada**:
   - Ofrecer consultar o importar estilos desde el catalogo interactivo de referencia: `https://ancient-prompt-design-flow.base44.app/`
   - O elegir uno de los 4 Arquetipos con Personalidad:
     - `precision-dark` / `precision-light`: Superficies monocromaticas oscuras/claras (estilo Linear / Raycast / Vercel), bordes de 1px de bajo contraste, tipografia geometrica y monoespaciada (`tabular-nums`) para metricas.
     - `warm-editorial`: Superficies calidas color papel/piedra (`#FAF8F5` / `#141413`, nunca blanco puro), titulares con serifa o sans humanista de alto contraste, aire y ritmo de lectura amplio (estilo Anthropic / Stripe Press / Read.cv).
     - `telemetry-grid`: Alta densidad de datos, rejillas tecnicas visibles, codigo de color semantico estricto (OK/Warn/Crit) sin ornamentos superfluos (estilo Grafana / Bloomberg / Industrial RF).
     - `neo-brutalist-craft`: Bordes solidos de 2px, sombras duras desplazadas sin desenfoque (`box-shadow: 4px 4px 0px`), acentos de alto impacto y micro-interacciones mecanicas (estilo Gumroad / Teenage Engineering).
3. **Modo de Color y Stack de Componentes**: Modo oscuro, claro o adaptativo, y primitivos de componentes (ej. Tailwind CSS + Radix / shadcn-ui).

Tras acordar las respuestas, generar `docs/brain/design.md` (presupuesto maximo: 80 lineas) y registrar su enlace en `docs/brain/index.md`.

## 4. Las 5 Leyes Duras Anti-Slop y Anti-Zombie UI
1. **Ley 1 — Prohibicion de Cliches de IA (Anti-Slop Ban List)**: Prohibidos los gradientes morados/indigo/cian por defecto sobre blanco o azul marino; prohibido el layout clonico de 'Hero centrado + 3 tarjetas con iconos circulares'; obligatoria la pareja tipografica con `tabular-nums` para datos numericos.
2. **Ley 2 — Cero Valores Magicos (Design Tokens Only)**: Prohibido hardcodear colores hexadecimales sueltos (`#3b82f6`) o pixeles arbitrarios en componentes. Todo elemento debe consumir tokens semanticos declarados en `docs/brain/design.md` (`surface`, `surface-elevated`, `text-primary`, `text-muted`, `border-subtle`, `accent-primary`).
3. **Ley 3 — Los 4 Estados Obligatorios (Anti-Zombie UI)**: Todo componente o vista asincrona con datos debe implementar explicitamente los 4 estados: `Loading` (skeletons con la geometria final), `Empty` (vacio util y disenado), `Error` (mensaje claro con accion de recuperacion) y `Populated`.
4. **Ley 4 — Jerarquia Espacial y Micro-interacciones**: Ritmo en multiplos de 4px/8px, estados `:hover`, `:active` y `:focus-visible` nitidos, transiciones de 150ms-220ms y respeto a `prefers-reduced-motion`.
5. **Ley 5 — Estructura Obligatoria de `docs/brain/design.md`**: El contrato debe contener obligatoriamente:
   - `## 1. Aesthetic Direction`
   - `## 2. Design Tokens`
   - `## 3. Typography & Spacing`
   - `## 4. Component & Anti-Slop Rules`

## 5. Semantic DOM & Live UI Inspection ("Agent Eyes")
Un agente que escribe UI sin inspeccionar el DOM vivo trabaja a ciegas; pero usar capturas de pantalla gigantes o HTML crudo agota el contexto. Siempre que se cree o modifique UI:

### 5.1 Auto-Bootstrap cuando el Proyecto empieza desde Cero o no tiene Navegador Configurado
Al activarse esta skill (tanto en un proyecto Greenfield donde se introduce UI por primera vez como en un proyecto Brownfield sin E2E), revisa `docs/brain/architecture.md`:
- Si `E2E / Browser UI Tests` esta en `N/A` y no dispones de una herramienta nativa de inspeccion semantica (`egolite`, Playwright MCP o Browser DOM Tool), **propon activamente al usuario configurarlo por el**:
  > "Detecto que vamos a desarrollar interfaz visual pero el proyecto aun no tiene configurado el verificador semantico de navegador ('Agent Eyes'). Como perfil backend no necesitas configurarlo a mano: si me das el OK, instalo Playwright ligero, creo el test base de Snapshot Semantico (`ariaSnapshot`) + chequeo responsive (`375px` y `1280px`) y actualizo `docs/brain/architecture.md`."
- Tras el OK del usuario, el agente ejecuta la configuracion segun el stack:
  - **Node / TypeScript / Next / Vite**: Instalar `@playwright/test` (`npm i -D @playwright/test && npx playwright install chromium`), crear `tests/e2e/ui-health.spec.ts` y actualizar `E2E / Browser UI Tests` en `docs/brain/architecture.md` a `npx playwright test`.
  - **Python (FastAPI / Flask / Django / Streamlit)**: Instalar `pytest-playwright` (`pip install pytest-playwright && playwright install chromium`), crear `tests/e2e/test_ui_health.py` y actualizar `docs/brain/architecture.md`.

### 5.2 Regla de Verificacion Visual en 3 Puntos (Pre-Completion Check)
Antes de marcar cualquier tarea de UI como `[x]` en `tasks.md`, el subagente constructor (`flash` / fast tier) debe verificar sobre el DOM renderizado y registrar en **Prueba Observada**:
1. **Semantic Accessibility Tree (`ariaSnapshot` / DOM Roles)**: Capturar el arbol semantico (`await page.locator('body').ariaSnapshot()` o equivalente en `egolite`/MCP) confirmando que existen los headings en jerarquia (`h1 -> h2`), botones/inputs con etiqueta accesible y los estados requeridos.
2. **Responsive Viewport & Overflow Check (`375x812` Mobile y `1280x800` Desktop)**: Evaluar en ambos tamanos de ventana que `document.documentElement.scrollWidth <= document.documentElement.clientWidth` (cero desbordamiento horizontal roto ni solapamientos).
3. **Zero Runtime / Console Errors**: Confirmar 0 errores en `page.on('pageerror')` y `console.error` al renderizar la vista.
