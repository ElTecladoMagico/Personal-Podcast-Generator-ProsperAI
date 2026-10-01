# 02 · `feat/frontend-skeleton`

**Objetivo:** SPA con identidad visual propia, login con Clerk, navegación y cliente tipado contra la API. Es la base sobre la que se construye toda la UX.
**Depende de:** 01. **ADRs:** 0001, 0005, 0014, 0015.

## Alcance
**Incluye:** scaffold de Vite, Tailwind 4 + shadcn, dirección de diseño (tokens, tipografía, movimiento), Clerk, rutas, AppShell, i18n EN/ES, TanStack Query, cliente generado desde OpenAPI, `netlify.toml`, landing.
**No incluye:** onboarding real, reproductor ni dashboard (solo páginas vacías con su título).

## Dirección de diseño (decidir y documentar en el commit 2)
Concepto: **"estudio de radio nocturno"**. Oscuro por defecto (con modo claro), un único color de acento cálido tipo piloto **ON AIR**, tipografía editorial para los titulares y sans neutra para la UI. Mucho espacio, movimiento suave con intención (nada gratuito).
- Fuentes de Google Fonts: display serif expresiva (p. ej. *Instrument Serif* o *Fraunces*) + UI sans (*Inter* o *Geist*). Elegir viendo una maqueta.
- Tokens CSS en `index.css` (`--background`, `--foreground`, `--accent`, `--muted`…) en el formato de shadcn, con contraste AA comprobado.
- Movimiento con `motion`: entradas de 150–250 ms, *spring* suave en los chips, respetando `prefers-reduced-motion`.
- Antes de cerrar el diseño, usar la skill `ecc:frontend-design-direction` (o `improve`) para una crítica, y guardar la decisión en `docs/design.md` (1 página: paleta, tipos, espaciado, movimiento, ejemplos de componentes).

## Commits (en orden)
1. **`chore(frontend): scaffold Vite React TS app`**: `npm create vite@latest frontend -- --template react-ts`; alias `@` → `src` en `vite.config.ts` y `tsconfig`; ESLint por defecto.
2. **`feat(frontend): Tailwind 4, shadcn and design tokens`**: `npm i tailwindcss @tailwindcss/vite`; `npx shadcn@latest init`; componentes base (`button card input badge dialog sheet tabs slider sonner skeleton tooltip dropdown-menu avatar separator`); fuentes, tokens y `docs/design.md`.
3. **`feat(frontend): Clerk authentication`**: desde `frontend/`, `clerk init --app app_3K65U9tWgI5ZMYza2Mn3R3JNn9e` (el CLI ya está instalado, logueado y el repo enlazado; detecta Vite + React, instala `@clerk/react` y escribe `VITE_CLERK_PUBLISHABLE_KEY` en `.env.local`). Revisar el diff que genere y quitar lo que sobre. `ClerkProvider` en `main.tsx` (error claro si falta la key); `afterSignOutUrl="/"`. Tema: `npm i @clerk/ui`, `appearance={{ theme: shadcn }}` (de `@clerk/ui/themes`) e `@import "@clerk/ui/themes/shadcn.css"` en `index.css`, así Clerk hereda los tokens de shadcn sin estilos a mano. Controles con `<Show when="signed-in">` / `<Show when="signed-out">`, `<SignInButton/>` y `<UserButton/>`. Cerrar con `clerk doctor`.
4. **`feat(frontend): routing and app shell`**: `npm i react-router`.
   - Rutas: `/` (landing si no hay sesión, `Home` si la hay), `/onboarding`, `/episodes/:id`, `/settings`, `/admin`, `*` → 404.
   - Componente `RequireAuth` (con `useAuth`: si `!isSignedIn`, redirige a `/`).
   - `AppShell`: barra superior con logo, navegación, selector de idioma de la UI y `<UserButton/>`. *Admin* solo visible si `me.is_admin`.
5. **`feat(frontend): typed API client with TanStack Query`**:
   - `npm i @tanstack/react-query` y `npm i -D openapi-typescript`;
   - script `gen:api`: `openapi-typescript $VITE_API_URL/openapi.json -o src/lib/api-types.ts`;
   - `lib/api.ts`: hook `useApi()` que devuelve `request<T>(path, init)` añadiendo `Authorization: Bearer ${await getToken()}` y lanzando un `ApiError` con `detail`;
   - `useMe()` con `useQuery`.
   - Si `me.onboarded === false`, `Home` redirige a `/onboarding`.
6. **`feat(frontend): UI i18n (EN/ES)`**: `lib/i18n.ts` con `const messages = {en: {...}, es: {...}}`, `I18nProvider` y `useT()`; idioma inicial según `navigator.language` y guardado en `localStorage`. Sin librerías.
7. **`feat(frontend): landing page`**: hero con propuesta de valor ("Your news, as a podcast made for you"), 3 beneficios (personalizado, llega solo a tu app de podcasts, puedes preguntar a los presentadores), CTA *Sign in*. Pensada para impresionar en 5 segundos: titular grande, visual animado (ondas de audio en CSS/SVG).
8. **`chore(frontend): Netlify config and env template`**: `netlify.toml` con `[build] base = "frontend"`, `command = "npm run build"`, `publish = "dist"` y la redirección SPA `/* /index.html 200`; `.env.example`.

## Verificación final
- `npm run lint && npm run build` en verde.
- Con backend local: login con Google → `Home` muestra el email de `/me` → la fila existe en `users`. **Primera prueba de punta a punta del JWT real** (valida `azp` con `http://localhost:5173`).
- Revisión visual a 1440 px y 390 px (landing y AppShell) + skill `improve`.

## Criterios de aceptación
- [ ] Login y logout funcionan; las rutas protegidas redirigen sin sesión.
- [ ] `api-types.ts` se genera y `useMe` está tipado.
- [ ] Modo oscuro y claro coherentes; `docs/design.md` existe.

## Riesgos y notas
- **Paquete de Clerk:** desde Core 3 el paquete es `@clerk/react` (no `@clerk/clerk-react`). Comprobado en la documentación de Clerk el 2026-10-01.
- **CORS:** si falla, revisar `CORS_ORIGINS` y que la petición lleve la cabecera `Authorization`.
