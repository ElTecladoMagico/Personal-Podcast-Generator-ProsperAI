# TDD · `feat/episode-pipeline`

**Plan:** [`docs/plans/06-episode-pipeline.md`](../plans/06-episode-pipeline.md). Resultados reales: [`06-resultados.md`](../plans/06-resultados.md).

## Recorridos
- Como oyente, pido un episodio y en unos 2 minutos tengo un MP3 con un guion verificado y tiempos por palabra.
- Como oyente, si algo falla a mitad, el reintento continúa donde se quedó sin repetir (ni pagar) lo anterior.
- Como oyente, nunca oigo una afirmación que las fuentes no respalden.

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| Coste de OpenAI (entrada en caché incluida) | `ModuleNotFoundError: app.llm` | 3 passed |
| ffmpeg: concatenar y medir | `ModuleNotFoundError: app.audio` | 2 passed |
| Orquestador: estados, tiempos, costes, reanudación, memoria | `ImportError: run` | 4 passed |
| Ventana de noticias (`since`) | 1 failed (función inexistente) | passed |
| Editor: validación y feedback por interés | `ModuleNotFoundError: editor` | 9 passed |
| Documentación con reservas | `ModuleNotFoundError: research` | 3 passed |
| Guionista: saneado, longitud, recorte | `ModuleNotFoundError: writer` | 4 passed |
| Verificador: eliminar turnos marcados, una revisión | `ModuleNotFoundError: checker` | 3 passed |
| Voz: tramos, palabras, línea de tiempo, `record()` | `ModuleNotFoundError: voice` | 5 passed |
| Audio firmado con `Range` | 3 failed (ruta inexistente) | 3 passed |
| **Reanudar tras un crash** (bug real, ver abajo) | 1 failed | passed |
| Recuperación al arrancar | `ImportError: jobs` | 1 passed |

**Bug cazado matando un proceso real durante `recording`:** el episodio quedaba en `status=recording` sin `failed_stage`, y el reintento empezaba desde `fetching` (volviendo a pagar editor, guion y verificación). Test añadido y corregido.

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | El coste usa la tarifa de caché para los tokens cacheados; todo modelo del pipeline tiene precio | `test_llm.py` |
| 2 | La concatenación conserva la duración real total | `test_audio.py` |
| 3 | Un episodio pasa por las 6 etapas, acaba `ready` con título, tiempos, costes, memoria de historias y evento `episode_ready` | `test_run.py::test_happy_path…` |
| 4 | Un fallo deja `failed` + `failed_stage` + evento; el reintento empieza en esa etapa y reutiliza el trabajo | `test_run.py::test_a_failing_stage…` |
| 5 | Un crash a mitad de etapa se reanuda en esa etapa | `test_run.py::test_an_interrupted…` |
| 6 | La ventana de noticias va desde el último episodio, entre 1 día y el valor por defecto (2 u 8 días) | `test_run.py::test_news_window…` |
| 7 | La selección del editor se rechaza con ids inexistentes, candidatos repetidos, número incorrecto o historias sin candidatos | `test_editor.py` |
| 8 | El feedback (👍/👎/saltos de 30 días) se agrupa por el interés de cada historia | `test_editor.py::test_feedback…` |
| 9 | Hasta 2 artículos de medios distintos por historia; las ilegibles se sustituyen por reservas; texto recortado a 6.000 | `test_research.py` |
| 10 | El guion solo lleva etiquetas de audio permitidas, sin URLs ni markdown; fuentes existentes y presentador válido; recorte de turnos de cierre si se pasa de largo | `test_writer.py` |
| 11 | Los turnos que siguen marcados tras la revisión se eliminan, y el capítulo que se queda sin hechos también; máximo 2 verificaciones y 1 reescritura | `test_checker.py` |
| 12 | Tramos ≤ 1.800 caracteres sin partir turnos ni cruzar capítulos; palabras sin etiquetas; tiempos con el desfase real de cada tramo; sin alineación fiable, se resalta por turno | `test_voice.py` |
| 13 | El MP3 se sirve solo con el token del dueño, responde 206 a `Range` y 410 si caducó | `test_audio_api.py` |
| 14 | Al arrancar se reenvían solo los episodios no terminados | `test_jobs.py` |

## Pruebas reales (ver resultados)
3 episodios de 2 min (es duo, en solo, es duo reanudado); verificador con dos errores plantados (ambos detectados y corregidos); comprobación del MP3 con ffmpeg (sin errores, duración de cabecera real, −15 LUFS).

## Cobertura y huecos
`uv run --with pytest-cov pytest --cov=app` → 87 % total, 91 tests. Sin cubrir sin red: las llamadas reales a OpenAI y ElevenLabs (`llm.parse`, `check_script`, `pick_stories`, `write_script`, `revise_script`, `synthesize`) y los `step()` que las encadenan. Se cubren con el CLI y las pruebas reales.
