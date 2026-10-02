# TDD · `feat/player`

**Plan:** [`docs/plans/09-player.md`](../plans/09-player.md).

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| `POST /events` | 5 failed, 1 passed (sin router) | 131 passed en el backend |
| Helpers de la línea de tiempo (`findActive`, `locate`, `chapterSegments`, `spokenText`, `isSkip`) | `Cannot find module './timeline'` | 28 passed en el frontend |

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | Los eventos del reproductor se guardan con usuario, episodio y `props` | `test_events_api.py::test_player_events_are_stored` |
| 2 | Solo los 5 tipos del frontend; los del servidor (`user_signed_up`…) → 422 | `…::test_only_frontend_event_types_are_accepted` |
| 3 | Episodio de otro usuario → 404 | `…::test_someone_elses_episode_is_404` |
| 4 | `props` > 2 KB → 413 | `…::test_props_over_2kb_are_rejected` |
| 5 | Cada fuente lleva su `story_id` | `test_episodes_api.py` |
| 6 | Capítulo/turno/palabra activos en un instante, también en el hueco entre capítulos; segmentos de la barra; etiquetas de audio fuera del texto; un seek > ½ capítulo es salto | `src/lib/timeline.test.ts` |

La UI (hooks de audio, transcripción, tarjetas, teclado, Media Session) se verificó en el navegador: ver las notas del plan.
