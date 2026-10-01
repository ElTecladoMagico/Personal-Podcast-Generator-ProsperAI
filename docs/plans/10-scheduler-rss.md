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
