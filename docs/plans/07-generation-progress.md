# 07 · `feat/generation-progress`

**Objetivo:** el usuario pulsa "Generar ahora" y **ve la redacción trabajando** paso a paso, con detalles reales ("42 artículos de 9 medios", "El editor eligió: …"), hasta que el episodio está listo. Primer momento "wow" del producto.
**Depende de:** 2, 6. **ADRs:** 0009, 0010, 0014.

## Backend (`routers/episodes.py`)
- `POST /episodes`:
  - 409 `{"detail": "Ya hay un episodio en producción"}` si el usuario tiene uno no terminal;
  - 400 si no ha hecho el onboarding;
  - 429 `{"detail": "Has alcanzado el límite de 5 episodios hoy"}` si ya tiene `MAX_MANUAL_EPISODES_PER_DAY` episodios `manual` creados en las últimas 24 h (los fallidos no cuentan);
  - crea el episodio con `trigger="manual"`, `status="queued"`, `prefs_snapshot` y `language`;
  - evento `episode_requested`; `run_in_pool(id)`; devuelve el episodio.
- `GET /episodes`: los del usuario, más recientes primero, sin `work` ni `script` (ligero): `id, status, title, summary, created_at, duration_s, topics, cover_seed`.
- `GET /episodes/{id}`: 404 si no es del usuario. Incluye:
  - `progress`, calculado de `work`: `{candidates: n, outlets: n_distintos, stories: [headline…], articles: n, issues_found, issues_fixed, recorded_chunks?: "3/6"}`;
  - `script` y `sources` (de `work.articles`: `{a1: {title, url, source, image_url}}`, sin textos) cuando está `ready`;
  - `audio_url = f"{PUBLIC_BASE_URL}/audio/{id}.mp3?k={feed_token}"`.
- `POST /episodes/{id}/retry`: solo si `failed` → `status=queued` (conserva `failed_stage`) → `run_in_pool`.
- Para `recorded_chunks`: el paso de voz guarda `work.recording = {"done": i, "total": n}` tras cada tramo (actualización barata) y la barra de progreso de "Grabando" avanza de verdad.

## Frontend
- **`Home`:**
  - cabecera con saludo según la hora ("Buenos días, Pedro") y el botón principal **"Generar ahora"**;
  - tarjeta del episodio más reciente (grande);
  - debajo, una cuadrícula con el resto.
  - Estado vacío: ilustración + "Tu primer episodio está a un clic".
- **`EpisodeCover`:** portada generativa determinista a partir de `cover_seed` (hash del id) y los temas: 2–3 gradientes radiales + textura de ruido SVG + iniciales del tema. Sin coste y única por episodio. Se reutiliza en la lista, el reproductor y Media Session (renderizada a `canvas` → `dataURL` en la rama 9).
- **`GenerationProgress`:** lista vertical de las 7 etapas (§6 del contrato) con:
  - icono, título y una línea de detalle real de `progress`: "📡 42 artículos de 9 medios", "🧠 El editor eligió 5 historias: …" (los titulares aparecen uno a uno con `motion`), "📚 8 artículos leídos", "✍️ Guion de ~9.000 caracteres", "🔎 3 afirmaciones corregidas", "🎙️ Grabando 3/6";
  - la etapa activa con un pulso animado y las completadas con un ✓ y una transición suave;
  - polling con `useQuery({refetchInterval: (q) => isTerminal(q.state.data?.status) ? false : 1500})`.
  - **`ready`:** transición a la tarjeta del episodio con el CTA "▶ Escuchar".
  - **`failed`:** mensaje legible + "Reintentar".
- Accesible: región `aria-live="polite"` que anuncia el cambio de etapa.

## Commits (en orden)
1. **`feat(api): create, list and get episodes`**: + tests (409, 429 por límite diario, 404 de otro usuario, 400 sin onboarding).
2. **`feat(api): retry failed episodes`**: + test.
3. **`feat(pipeline): expose recording progress in work`**.
4. **`chore(frontend): regenerate API types`**.
5. **`feat(frontend): generative episode cover`**.
6. **`feat(frontend): home with generate button and episode grid`**.
7. **`feat(frontend): live generation progress`**.
8. **`feat(frontend): failed state and retry`**.

## Verificación final
- Local: onboarding provisional (preferencias insertadas por SQL o con el CLI) → "Generar ahora" → se ven las 7 etapas con detalles reales → "Escuchar" lleva a `/episodes/:id` (vacía hasta la rama 9).
- Forzar un fallo (key de ElevenLabs incorrecta) → `failed` en `recording` → corregir → "Reintentar" → termina sin repetir el editor.
- Revisión visual 1440/390 + `improve`.

## Criterios de aceptación
- [ ] No se pueden lanzar dos generaciones a la vez para el mismo usuario, ni más de 5 manuales al día.
- [ ] La UI refleja cada etapa en ≤ 2 s.
- [ ] Reintentar desde la UI reanuda en la etapa que falló.
