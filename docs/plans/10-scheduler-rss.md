# 10 · `feat/scheduler-rss`

**Objetivo:** los episodios **llegan solos**: se generan según el horario de cada usuario, aparecen en su app de podcasts vía RSS privado y los audios antiguos se limpian.
**Depende de:** 6, 8. **ADRs:** 0004, 0010, 0011.

## Programador (`app/jobs.py`)
- `BackgroundScheduler` de APScheduler 3.x, arrancado en el `lifespan` si `SCHEDULER_ENABLED` (desactivado en tests) y parado al apagar.
- **Job `enqueue_due_episodes`** (cada 10 min, `max_instances=1`, `coalesce=True`):
  ```sql
  SELECT * FROM users
  WHERE next_run_at <= now() AND onboarded_at IS NOT NULL AND NOT is_mock
  FOR UPDATE SKIP LOCKED
  ```
  Por cada usuario:
  - si no tiene un episodio en curso → crea uno `scheduled` y `run_in_pool`;
  - en cualquier caso, `next_run_at = compute_next_run(schedule, now)` (nunca se acumulan ejecuciones atrasadas).
  - **Antelación:** `compute_next_run` (rama 8) ya devuelve la hora del usuario **menos 20 min** (`GENERATION_LEAD_MIN`), para que el episodio esté listo *a* esa hora.
  - `FOR UPDATE SKIP LOCKED` deja preparado el camino a varias instancias (ADR 0010).
- **Job `cleanup_audio`** (diario, 04:00 UTC): episodios `ready` con `finished_at < now − 30 días` y `audio_expired = false` → borra `AUDIO_DIR/<user>/<episode>.mp3` y la carpeta `AUDIO_DIR/<user>/<episode>/` (respuestas de "Preguntar") → `audio_expired = true`.

## RSS (`app/rss.py` + `routers/feeds.py`)
- `GET /feeds/{feed_token}.xml` → 404 si el token no existe. `Content-Type: application/rss+xml; charset=utf-8`.
- Se construye con `xml.etree.ElementTree` y los espacios de nombres `itunes` y `podcast`.
  - **Canal:**
    - `title` "<Nombre>'s Daily Brief" / "El podcast de <Nombre>";
    - `description`, `language` y `itunes:author` "Personal Podcast Generator";
    - `itunes:image` (portada estática `GET /static/cover.png`, 3000×3000 PNG);
    - `itunes:category` News;
    - `itunes:explicit` false;
    - `itunes:block` yes (privado: que no lo indexe el directorio).
  - **Ítems:** episodios `ready` sin `audio_expired`, los 50 más recientes:
    - `title`;
    - `description` (summary + lista HTML de fuentes con enlaces);
    - `enclosure url="{audio_url}&src=rss" length=<bytes> type="audio/mpeg"`;
    - `guid isPermaLink="false"` = id;
    - `pubDate` (RFC 2822 con `email.utils.format_datetime`);
    - `itunes:duration` (segundos);
    - `podcast:chapters` → `GET /feeds/{token}/chapters/{episode_id}.json` (formato JSON Chapters de Podcasting 2.0: `{"version":"1.2.0","chapters":[{"startTime","title","url"}]}`). Lo usan Pocket Casts y otras apps.
- **Evento `feed_download`:** en `/audio/...` cuando `src=rss` y la petición empieza en el byte 0 (con o sin `Range`), para no contar cada trozo.
- **Portada:** `scripts/make_cover.py` (Pillow como dependencia de desarrollo) genera `app/static/cover.png` con el estilo de `docs/design.md`; se versiona.

## Frontend
- **Ajustes → "Escúchalo en tu app de podcasts":**
  - URL del feed con "Copiar";
  - botones **Apple Podcasts** (`podcast://<host>/feeds/<token>.xml`), **Overcast** (`overcast://x-callback-url/add?url=<url>`) y **Pocket Casts** (`pktc://subscribe/<host>/feeds/<token>.xml`), con una nota de que funcionan desde el móvil o el Mac con la app instalada;
  - "Regenerar enlace" (diálogo de confirmación: "las suscripciones actuales dejarán de recibir episodios") → `POST /me/feed-token/rotate`.
- **`Home`:** "Próximo episodio: mañana a las 07:00" a partir de `next_run_at + GENERATION_LEAD_MIN` (en la zona horaria del usuario), o "Solo a demanda".

## Commits (en orden)
1. **`feat(jobs): scheduler with due-episode enqueue`** + tests (usuario pendiente → 1 episodio y `next_run_at` avanzado; usuario con uno en curso → no crea otro pero avanza; `is_mock` → ignorado).
2. **`feat(jobs): 30-day audio cleanup`** + test con ficheros temporales.
3. **`chore(scripts): podcast cover artwork`**.
4. **`feat(api): private RSS feed and JSON chapters`** + tests (XML válido, etiquetas obligatorias, solo episodios del dueño, sin los expirados).
5. **`feat(api): feed token rotation and feed_download tracking`** + tests.
6. **`feat(frontend): podcast app subscription and next episode info`**.

## Verificación final
- Local: poner la hora de un usuario a ahora + 21 min → en ≤ 10 min se crea el episodio `scheduled`.
- Producción:
  - suscribirse en Apple Podcasts (macOS: Archivo → Seguir un programa por URL) y en Pocket Casts → aparecen los episodios con duración y capítulos (Pocket Casts);
  - programar uno para dentro de 30 min y comprobar que llega solo.
- **Memoria:** dos episodios seguidos con los mismos intereses → el segundo no repite historias, o las presenta como seguimiento ("como os contamos…").
- Validar el feed con https://podba.se/validate/ (o un validador equivalente).

## Criterios de aceptación
- [ ] Nunca se generan dos episodios simultáneos para un usuario ni ejecuciones duplicadas.
- [ ] El RSS funciona en al menos 2 apps reales.
- [ ] Los audios de más de 30 días se borran y el episodio sigue visible con su transcripción.

## Notas de implementación (2026-10-02)
- **Sin APScheduler:** un hilo `daemon` de la biblioteca estándar (`jobs.schedule_forever`) que cada **60 s** llama a `enqueue_due` y `cleanup_audio`. La consulta es barata e indexada; un minuto hace que el episodio empiece casi a su hora (con 10 min podía empezar 10 min tarde). Sin dependencia nueva ni job de las 04:00: la limpieza es otra consulta en el mismo tic.
- **Sin `FOR UPDATE SKIP LOCKED`:** hay un solo proceso (ADR 0010). El `next_run_at` se avanza y se confirma **antes** de crear el episodio (nunca se repite un hueco), y el índice único parcial ya impide dos episodios a la vez (`IntegrityError` → se salta). Marcado con `ponytail:` en el código con el camino de mejora.
- **Sin capítulos JSON (`podcast:chapters`):** YAGNI; el feed funciona en cualquier app sin ellos. Se añaden si se quieren capítulos en Pocket Casts.
- **Un solo fichero para el feed** (`routers/feeds.py`, ElementTree) en lugar de `rss.py` + router. Título y descripción en el idioma del oyente.
- **`/me` devuelve `next_episode_at`** (la hora a la que estará listo) en vez de `next_run_at`: los 20 min de antelación se quedan en el backend y el frontend solo formatea ("Próximo episodio: sábado, 07:00", en la zona del oyente).
- **`audio_url()`** en `storage.py`, compartido por el detalle del episodio y el feed.
- **Portada:** `scripts/make_cover.py` con `uv run --with pillow` (Pillow no entra en las dependencias), 3000×3000, 112 KB, servida en `/static/cover.png`.
- **Verificación local:** Home muestra el próximo episodio; Ajustes → copiar, enlaces de Apple Podcasts/Overcast/Pocket Casts correctos, "Regenerar enlace" con confirmación → el enlace viejo da 404 y el nuevo devuelve el feed. 390 px sin scroll horizontal; Lighthouse móvil de Ajustes: accesibilidad 97 (el único fallo, `target-size`, son los puntos de importancia de la rama 8; arreglarlo exige rediseñar el chip), buenas prácticas 100, SEO 100.
- **Pendiente:** verificación en producción (suscripción real en Apple Podcasts y Pocket Casts, episodio programado que llega solo, validador de feeds).
- Informe TDD: [`docs/testing/10-scheduler-rss.tdd.md`](../testing/10-scheduler-rss.tdd.md).

## Revisión general antes de fusionar (2026-10-02)
Revisión crítica de lo construido en las ramas 2–10. Arreglado, cada punto con su test (RED → GREEN) y la suite completa en verde:
- **Feed en apps reales:** el feed y el audio respondían 405 a `HEAD`, que Apple Podcasts y otras apps usan para comprobar el episodio → ahora `GET`+`HEAD` (HEAD no cuenta como descarga). Esas dos rutas salen del OpenAPI (GET+HEAD duplicaba el *operation id* y rompía los tipos generados). El `<link>` del canal apuntaba a la API (404) → `APP_URL` (`https://podcast.scuda.es`). Comprobado con `feedparser` (sin errores) y con `curl -I` contra uvicorn.
- **Ajustes → podcasts:** fuera Overcast (su enlace solo funciona en iPhone); quedan Apple Podcasts (Mac e iPhone) y Pocket Casts, más la nota "pégalo en *Añadir por URL*" para cualquier otra app.
- **Duración:** se ofrecían 20 min pero producción limita a 10 (`EPISODE_MAX_MINUTES`) → solo 5 y 10. Migración de datos `c3d1e7a9f2b4` (20 → 10 en preferencias y *snapshots*).
- **Idiomas:** FR/DE/IT/PT no tenían voces nativas ni prompt probado → solo español e inglés (`Language = Literal["es","en"]`); la importación ignora otros idiomas y conserva el elegido; selector de dos botones. Migración `d8f2a4c6b1e3` (otros → `en`, que ya usaban voces inglesas).
- **Puntos de importancia:** 24 px de área táctil en pantallas táctiles (`pointer-coarse:`), compactos con ratón. Lighthouse móvil de Ajustes: accesibilidad **100**.
- **👍/👎:** el detalle del episodio devuelve `votes` (último voto por historia), y el reproductor los muestra tras recargar.

Revisado y sin cambios: el feedback y los saltos sí llegan al editor (`feedback_by_interest`); pesos, temas a evitar, medios de confianza, tono y profundidad sí llegan a fuentes, editor y guionista. Riesgos conocidos que se documentan en `solution.md`: el resolutor de Google News (frágil, términos de uso), Clerk en modo desarrollo, y que "Generar ahora" justo antes de la hora programada salta el programado de ese día (intencionado: evita dos episodios casi iguales).
