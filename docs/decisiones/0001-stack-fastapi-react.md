# 0001 · Stack: FastAPI (Python) + React/Vite/shadcn

**Estado:** Aceptada

## Contexto
Necesitamos un backend que descargue y procese noticias (RSS, APIs, scraping), llame a LLMs y TTS y genere audio, y un frontend con UX muy cuidada. El autor debe poder explicar cada parte.

## Decisión
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy/SQLModel.
- **Frontend:** React + Vite + TypeScript + shadcn/ui + Tailwind, como SPA estática.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **FastAPI + React/Vite (elegida)** | Python tiene el mejor ecosistema para scraping (trafilatura), feeds (feedparser) y SDKs de IA. La SPA es estática y se hostea gratis (Netlify). Separación clara frontend/backend, fácil de explicar. | Dos lenguajes. CORS entre dominios. Hay que tipar el contrato API dos veces (mitigable generando tipos TS desde OpenAPI). |
| Next.js monolito (TS) | Un lenguaje, server actions, Clerk y shadcn nativos | Scraping y extracción de texto más pobres en Node. Los procesos largos y el cron encajan mal en serverless. |
| FastAPI + HTMX/Streamlit | Un solo lenguaje, muy rápido de construir | Techo de UX bajo: no permite el reproductor inmersivo que queremos. |
| Django + React | Admin gratis y ORM maduro | Más peso y convenciones de las necesarias para una API pequeña. |

## Consecuencias
- El frontend llama al backend con `Authorization: Bearer <JWT de Clerk>`. Sin cookies entre dominios, así que no hay problemas de SameSite.
- CORS restringido al dominio de Netlify.
- Tipos del cliente generados desde el OpenAPI de FastAPI (`openapi-typescript`) para no duplicar a mano.

## Revisar si
El equipo pasa a ser solo TS, o el backend necesita SSR o SEO (no es el caso).
