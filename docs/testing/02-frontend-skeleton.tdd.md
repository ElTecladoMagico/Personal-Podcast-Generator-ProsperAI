# TDD · `feat/frontend-skeleton`

**Plan:** [`docs/plans/02-frontend-skeleton.md`](../plans/02-frontend-skeleton.md). Runner: `npm test` (vitest).

## Recorridos de usuario
- Como visitante, veo la landing en mi idioma (navegador o el que elegí) y puedo entrar.
- Como usuario, al entrar la app me reconoce (`/me`) y me lleva al onboarding si aún no lo hice.
- Como usuario, si la API falla veo un mensaje legible (el `detail` del backend).

## Ciclos RED → GREEN

| Tarea | RED | GREEN |
|---|---|---|
| i18n: idioma inicial y diccionarios | `npm test` → *Test Files 1 failed* (no existía `./i18n`) | 4 passed |
| Cliente API (`apiFetch`) | `npm test` → `Cannot find module './api'` | 9 passed (total) |

## Qué garantizan los tests

| # | Garantía | Test | Tipo |
|---|---|---|---|
| 1 | El idioma guardado manda; si no, el del navegador; si no es EN/ES (o hay basura guardada), inglés | `src/lib/i18n.test.ts` | unidad |
| 2 | El diccionario ES tiene exactamente las mismas claves que EN | `src/lib/i18n.test.ts` | unidad |
| 3 | `apiFetch` envía `Authorization: Bearer` solo si hay token y usa `VITE_API_URL` | `src/lib/api.test.ts` | unidad (fetch simulado) |
| 4 | Los errores `{detail}` se convierten en `ApiError` con estado y mensaje; los no-JSON caen a `HTTP <status>` | `src/lib/api.test.ts` | unidad |
| 5 | 204 devuelve `undefined` sin intentar parsear | `src/lib/api.test.ts` | unidad |

**E2E manual** (Chrome DevTools): login real con Clerk → `GET /me` 200 con el `azp` del navegador → usuario y evento creados → redirección a `/onboarding`; `Home` con usuario ya configurado. Landing a 1440 px y 390 px en oscuro y claro. Lighthouse móvil: accesibilidad 100.

## Huecos
Los componentes (landing, AppShell, rutas) no tienen tests unitarios: son presentación y se verificaron en el navegador. Los tests E2E automatizados (Playwright) no compensan todavía; el registro de Clerk tiene CAPTCHA.
