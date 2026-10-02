# TDD · `feat/scheduler-rss`

**Plan:** [`docs/plans/10-scheduler-rss.md`](../plans/10-scheduler-rss.md).

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| Programador y limpieza | `AttributeError: module 'app.jobs' has no attribute 'enqueue_due'` (×3) / `'cleanup_audio'` | 4 passed (135 en total) |
| Feed RSS, `feed_download`, rotación del token | 3 failed (404 sin ruta, 0 descargas, `KeyError: 'feed_url'`) | 4 passed (139 en total) |
| `/me` → `next_episode_at` | `KeyError: 'next_episode_at'` (2 failed) | 139 passed |
| Enlaces de apps y etiqueta del próximo episodio | `Cannot find module './feed'` | 3 passed (31 en el frontend) |

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | Un usuario con el hueco vencido recibe **un** episodio `scheduled` y su `next_run_at` pasa al día siguiente (06:40 UTC → 07:00 Madrid) | `test_scheduler.py::test_due_user…` |
| 2 | Con un episodio en curso no se crea otro, pero el hueco avanza (no se acumulan) | `…::test_user_with_an_episode_in_progress…` |
| 3 | Usuarios `is_mock`, sin onboarding, con hueco futuro o sin horario → ignorados | `…::test_mock_not_onboarded…` |
| 4 | Audios > 30 días se borran y el episodio queda `audio_expired`; los de 29 días no; lo ya caducado no se toca otra vez | `…::test_audio_older_than_30_days…` |
| 5 | El feed solo lista episodios `ready` del dueño con audio vigente; título en su idioma, `itunes:block`, portada, `enclosure` con tamaño real y `src=rss`, `guid`, `pubDate` RFC 2822, duración | `test_feeds_api.py::test_feed_lists_only…` |
| 6 | Token desconocido → 404 | `…::test_unknown_feed_is_404` |
| 7 | `feed_download` cuenta la descarga desde el byte 0 (con o sin `Range`), no los trozos siguientes ni el reproductor web | `…::test_feed_download_counts_once…` |
| 8 | Regenerar el token mata el feed anterior y el nuevo funciona | `…::test_rotating_the_token…` |
| 9 | `next_episode_at` es la hora del oyente (07:00), `null` sin horario | `test_preferences_api.py`, `test_me.py` |
| 10 | Enlaces `podcast://`, `overcast://`, `pktc://`; "sábado, 07:00" / "Saturday 01:00" según la zona | `src/lib/feed.test.ts` |

## Revisión general (RED → GREEN)
| Arreglo | RED | GREEN |
|---|---|---|
| `HEAD` en feed y audio; `<link>` a la web | `405 == 200`; `'http://localhost:8000' == 'https://podcast.scuda.es'` | 140 passed |
| Solo Apple Podcasts y Pocket Casts | 1 failed (`podcastApps`) | 31 passed |
| Duración 5 o 10 min | `DID NOT RAISE` (20 aceptado) | 141 passed |
| Solo `es`/`en` (y la importación ignora otros) | 2 failed | 143 passed |
| Votos guardados en el detalle | `KeyError: 'votes'` | 144 passed |

Migraciones de datos probadas con una fila temporal dentro de una transacción revertida (20 → 10, `fr` → `en`). Puntos de importancia: Lighthouse móvil `target-size` en verde (accesibilidad 100).
