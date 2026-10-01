# Planes de implementación por rama

Esta carpeta es la **fuente de verdad para ejecutar el proyecto**. Si se pierde el contexto de la conversación, todo lo necesario para continuar está aquí y en [`../decisiones/`](../decisiones/README.md).

## Cómo usar estos planes
1. Leer [`00-contratos.md`](00-contratos.md): estructura del repo, variables de entorno, modelo de datos, esquemas JSON, endpoints, eventos, voces y convenciones. **Todas las ramas lo respetan.** Si una rama necesita cambiar un contrato, actualiza ese fichero en el mismo commit que el código.
2. Ejecutar las ramas **en orden**. Cada plan indica de qué depende.
3. Por cada rama:
   - `git switch main && git pull && git switch -c <rama>`;
   - seguir los **commits del plan en orden** (son atómicos: uno por paso);
   - pasar la **verificación** y los **criterios de aceptación**;
   - revisar el código (ver "Calidad");
   - `git switch main && git merge --no-ff <rama> && git push`;
   - marcar la rama como ✅ en la tabla de abajo (commit `docs: mark <rama> done`).
4. Si algo del plan resulta incorrecto al implementarlo, **se corrige el plan** (y el ADR si aplica) en la misma rama, explicando por qué.

## Estado

| # | Rama | Plan | Depende de | Estado |
|---|---|---|---|---|
| 1 | `feat/backend-skeleton` | [01](01-backend-skeleton.md) | — | ✅ |
| 2 | `feat/frontend-skeleton` | [02](02-frontend-skeleton.md) | 1 | ✅ |
| 3 | `chore/deploy` | [03](03-deploy.md) | 1, 2 | ⏳ |
| 4 | `spike/google-news` | [04](04-spike-google-news.md) | 1 | ⏳ |
| 5 | `feat/news-sources` | [05](05-news-sources.md) | 4 | ⏳ |
| 6 | `feat/episode-pipeline` | [06](06-episode-pipeline.md) | 5 | ⏳ |
| 7 | `feat/generation-progress` | [07](07-generation-progress.md) | 2, 6 | ⏳ |
| 8 | `feat/onboarding` | [08](08-onboarding.md) | 2, 6 | ⏳ |
| 9 | `feat/player` | [09](09-player.md) | 7 | ⏳ |
| 10 | `feat/scheduler-rss` | [10](10-scheduler-rss.md) | 6, 8 | ⏳ |
| 11 | `feat/ask-hosts` | [11](11-ask-hosts.md) | 9 | ⏳ |
| 12 | `feat/admin-dashboard` | [12](12-admin-dashboard.md) | 9, 10 | ⏳ |
| 13 | `docs/solution` | [13](13-solution.md) | todas | ⏳ |

Desplegamos al final de la rama 3 y **después de cada merge** a partir de ahí (runbook en `deploy/README.md`, creado en la rama 3).

## Tareas manuales del autor (no automatizables por Claude)

| Cuándo | Tarea | Resultado esperado |
|---|---|---|
| ✅ Antes de la rama 1 | Crear una aplicación en **Clerk** (Google + email). Hecho: app `app_3K65U9tWgI5ZMYza2Mn3R3JNn9e`; Claude obtiene las claves con el CLI (`clerk env pull`). | `VITE_CLERK_PUBLISHABLE_KEY`, `CLERK_ISSUER` |
| ✅ Antes de la rama 1 | *Custom claims* del token de sesión: `{"metadata": "{{user.public_metadata}}", "email": "{{user.primary_email_address}}", "name": "{{user.first_name}}"}`. Hecho por Claude con `clerk config patch` (ver README raíz). | El JWT lleva el rol de admin, el email y el nombre |
| Antes de la rama 5 | Pedir una key gratuita en https://open-platform.theguardian.com/access/ | `GUARDIAN_API_KEY` (mientras tanto vale `test`) |
| Antes de la rama 6 | Mirar los créditos restantes de ElevenLabs en su panel | Presupuesto de pruebas |
| Rama 3 | Crear el sitio en **Netlify** enlazando el repo de GitHub (`scuda-podcast`) | `scuda-podcast.netlify.app` |
| Rama 3 | DNS: `podcast.scuda.es` CNAME → `scuda-podcast.netlify.app` (el A de `api.podcast.scuda.es` ya está) | HTTPS en ambos |
| Rama 3 | Clerk producción: añadir los registros DNS que pida Clerk para `scuda.es` (o seguir en modo desarrollo; ver plan 03) | Login sin la marca "Development" |
| Cuando quieras | Clerk → Configure → *Application name*: cambiar "ProsperAI_challenge" por "Personal Podcast" (es lo que se ve en el modal de login) | Login con la marca del producto |
| Rama 12 | Marcar tu usuario como admin: Clerk → Users → *public metadata* `{"role":"admin"}` | Acceso a `/admin` |

## Calidad (en cada rama, antes de mergear)
- **ponytail** activo siempre: la solución más simple que funcione, sin abstracciones especulativas.
- Tests mínimos de la lógica no trivial (ver cada plan). `uv run pytest` y `npm run build` en verde.
- `uv run ruff check . && uv run ruff format --check .` (backend) y `npm run lint` (frontend).
- Revisión: `/code-review` sobre el diff de la rama; en ramas grandes (6, 9, 12), además la skill `thermo-nuclear-code-quality-review`.
- UI: en ramas visuales (2, 7, 8, 9, 11, 12), revisar en el navegador a 1440 px y a 390 px (viewport emulado: la ventana no baja de 500 px) con el checklist de `ecc:frontend-design-direction` y un Lighthouse de accesibilidad (objetivo 100). La skill `improve` de shadcn no sirve para esto (es un auditor de código de solo lectura que genera planes para otro agente): se usa una vez en la rama 13 como auditoría final.
- E2E con Clerk: el registro tiene CAPTCHA (Cloudflare Turnstile), así que el usuario de pruebas se crea con `clerk api /users` (email `…+clerk_test@example.com`, contraseña) y en el navegador solo se hace login; el código de verificación de los emails `+clerk_test` es `424242`. Borrar el usuario al terminar.
- Ningún secreto en commits: `.env` está en `.gitignore`; solo se versionan los `.env.example`.
