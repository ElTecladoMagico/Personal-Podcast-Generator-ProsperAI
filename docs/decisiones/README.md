# Registro de decisiones (ADR)

Cada decisión de arquitectura o producto se documenta en un fichero propio con: contexto, decisión, alternativas evaluadas con sus tradeoffs, consecuencias y cuándo revisarla.

Principios que guían todas las decisiones:
1. **Lógica lo más simple posible**: cada pieza debe poder explicarse en una frase.
2. **UX impresionante**: donde invertimos complejidad, que se note para el usuario.
3. **Producto multiusuario real**: cuentas, datos persistentes, acceso concurrente.

| # | Decisión | Estado |
|---|---|---|
| [0001](0001-stack-fastapi-react.md) | Stack: FastAPI + React/Vite/shadcn | Aceptada |
| [0002](0002-despliegue.md) | Despliegue: frontend en Netlify, backend en VPS Hetzner compartida (docker compose) | Aceptada |
| [0003](0003-base-de-datos.md) | Base de datos: PostgreSQL | Aceptada |
| [0004](0004-almacenamiento-audio.md) | Almacenamiento de audio: volumen local | Propuesta |
| [0005](0005-autenticacion.md) | Autenticación: Clerk | Aceptada |
| [0006](0006-fuentes-de-noticias.md) | Fuentes de noticias: RSS + APIs + scraping selectivo | Propuesta |
| [0007](0007-llm.md) | LLM: OpenAI | Propuesta |
| [0008](0008-tts.md) | Voz: ElevenLabs Text to Dialogue | Propuesta |
| [0009](0009-pipeline-de-episodio.md) | Pipeline del episodio: "redacción" en 5 pasos | Propuesta |
| [0010](0010-programacion-y-ejecucion.md) | Programación y ejecución: APScheduler + tareas en proceso | Propuesta |
| [0011](0011-entrega-rss-privado.md) | Entrega: feed RSS privado por usuario | Propuesta |
| [0012](0012-onboarding-importar-desde-ia.md) | Onboarding: importar intereses desde tu IA | Aceptada |
| [0013](0013-dashboard-de-metricas.md) | Dashboard interno de métricas | Propuesta |
| [0014](0014-ux-reproductor-inmersivo.md) | UX: reproductor inmersivo | Aceptada |
| [0015](0015-idioma-elegible.md) | Idioma del podcast elegible por usuario | Aceptada |

Diagrama: [`../arquitectura/architecture.html`](../arquitectura/architecture.html) (fuente: `architecture.json`, generado con archify).
