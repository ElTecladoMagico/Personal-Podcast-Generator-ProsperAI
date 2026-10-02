# TDD · `feat/generation-progress`

**Plan:** [`docs/plans/07-generation-progress.md`](../plans/07-generation-progress.md).

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| API de episodios (crear, límites, progreso, detalle listo, 404 ajeno, reintentar) | `ImportError: episodes` | 8 passed; el índice parcial hizo fallar un test antiguo (3 activos por usuario), corregido |
| Lógica del frontend: etapas, fin del polling, saludo, semilla de portada | `Cannot find module './episodes'` | 7 passed |
| `format()` de i18n | test añadido | passed |

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | "Generar ahora" crea un episodio `queued` y lo manda al pool; aparece el primero en la lista | `test_episodes_api.py::test_generate_now…` |
| 2 | Sin onboarding → 400 | `…::test_requires_onboarding` |
| 3 | Un solo episodio en producción por usuario (409), garantizado por la BD | `…::test_one_episode_in_progress…` |
| 4 | Límite diario de episodios manuales (429), sin contar los fallidos, ventana de 24 h | `…::test_daily_limit…` |
| 5 | `progress` refleja los números reales de cada etapa | `…::test_progress_reports…` |
| 6 | Episodio listo: `audio_url` firmado con el `feed_token` del dueño y `sources` sin el texto de los artículos | `…::test_ready_episode…` |
| 7 | Episodios de otro usuario → 404 (también al reintentar) | `…::test_other_users…` |
| 8 | Solo se reintenta lo fallido; conserva `failed_stage` y se reenvía al pool | `…::test_retry_only_failed…` |
| 9 | Estados de las 7 etapas (hecha, activa, pendiente, fallida); el polling para en `ready`/`failed`; saludo por franja; portada determinista | `src/lib/episodes.test.ts` |

E2E real en el navegador, incluido el camino de fallo y reintento: ver las notas del plan.
