# TDD · `feat/ask-hosts`

**Plan:** [`docs/plans/11-ask-hosts.md`](../plans/11-ask-hosts.md).

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| Capítulo en juego, limpieza de la respuesta, endpoint y audio | `ModuleNotFoundError: app.pipeline.ask` | 7 passed (163 en total) |
| La limpieza de 30 días borra las respuestas | `assert not True` (la carpeta seguía) | 4 passed |
| Métrica de "Preguntar" en el dashboard | `KeyError: 'ask'` | 6 passed |
| Preguntas simuladas en el seed | `assert (0 > 0)` | 2 passed |
| Punto de reanudación y turno activo | `Cannot find module './ask'` | 3 passed (38 en el frontend) |

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | La pregunta va sobre la historia que suena; en intro/despedida, la más cercana | `test_ask.py` |
| 2 | La respuesta se limpia como el guion (presentador válido, solo fuentes conocidas, sin markdown ni URLs) y se corta si se alarga | `test_ask.py` |
| 3 | El prompt lleva la pregunta y los textos del capítulo; suenan las voces de cada presentador; el audio se sirve; queda `ask_asked` con capítulo, latencia y caracteres | `test_ask_api.py::test_hosts_answer…` |
| 4 | Sin el token del feed no hay audio; un `qid` raro → 404 | `…::test_the_answer_audio_needs_the_feed_token` |
| 5 | Solo episodios listos (409) y preguntas de 3–300 caracteres (422) | `…::test_only_ready_episodes…` |
| 6 | Máximo 10 preguntas por episodio y hora (429) | `…::test_ten_questions…` |
| 7 | La limpieza de 30 días borra también la carpeta de respuestas | `test_scheduler.py` |
| 8 | Adopción y latencia p50/p95 de "Preguntar" | `test_metrics.py` |
| 9 | Reanudar 2 s antes (sin bajar de 0); turno activo por proporción de caracteres | `src/lib/ask.test.ts` |

Prueba real con LLM y voz, y E2E en el navegador: ver las notas del plan.
