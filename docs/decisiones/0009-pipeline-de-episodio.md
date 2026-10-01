# 0009 · Pipeline del episodio: una "redacción" en 6 pasos con verificación de hechos

**Estado:** Aceptada

## Contexto
Prioridad nº 1: que la lógica sea simple y explicable. La metáfora de una redacción de radio hace que cada paso tenga un rol obvio.

## Decisión
Una función `generate_episode(episode_id)` que ejecuta en orden y guarda `episode.status` tras cada paso:

| Paso | Rol | Qué hace | Estado |
|---|---|---|---|
| 1 | Reportero | Recoge unos 40 candidatos de las fuentes ([0006](0006-fuentes-de-noticias.md)) | `fetching` |
| 2 | Editor (LLM mini) | Elige 5–7 historias, agrupa duplicados de varios medios y marca seguimientos. Recibe: intereses con peso, feedback previo e historias ya contadas. | `editing` |
| 3 | Documentación | Scraping del texto completo solo de las elegidas | `researching` |
| 4 | Guionista (LLM) | JSON `{title, chapters[{story_id, turns[{speaker, text, source_ids}]}]}` según formato, tono, duración e idioma | `writing` |
| 5 | Verificador (LLM) | Comprueba cada turno contra el texto de sus `source_ids`. Devuelve los turnos con afirmaciones no respaldadas, exageradas o mal atribuidas, y el guionista los reescribe (una sola ronda; si alguno sigue sin respaldo, se elimina). | `verifying` |
| 6 | Locutores | ElevenLabs por tramos → MP3 unido con ffmpeg ([0016](0016-montaje-de-audio-ffmpeg.md)) + tiempos ([0008](0008-tts.md)) | `recording` → `ready` |

Si falla, `failed` con la etapa y el error. El reintento rehace desde la etapa fallida porque los resultados intermedios se guardan en el episodio.

**Memoria y seguimientos:** al terminar, cada historia se guarda en `stories` (título y resumen). El editor recibe las de los últimos 14 días: no las repite salvo que haya novedad, y en ese caso el guionista dice "como os contamos el martes…".

## Alternativas descartadas

| Opción | Por qué no |
|---|---|
| Deduplicación y ranking con embeddings + clustering | Más código, más conceptos (vectores, umbrales). El editor LLM hace lo mismo y se explica en una frase. |
| Framework de agentes (LangGraph, CrewAI) | Abstracción innecesaria para 5 pasos secuenciales |
| Cola de tareas por etapa | Ver [0010](0010-programacion-y-ejecucion.md) |

## Por qué sí verificamos (decisión del autor)
Los episodios programados se generan mientras el usuario **no está esperando**, así que la latencia extra (~20–40 s) no se nota. En un producto de noticias, la fidelidad a los hechos vale más que ese coste. Para mantener un único camino de código, la verificación también corre en "Generar ahora"; la UI de progreso lo muestra como un paso más ("🔎 Comprobando los hechos…"). El informe del verificador (turnos señalados y corregidos) se guarda en el episodio y alimenta una métrica del dashboard: *% de turnos corregidos*.

Alternativas consideradas para la verificación:
| Opción | Pros | Contras |
|---|---|---|
| **Verificador LLM + una ronda de reescritura (elegida)** | Detecta afirmaciones sin respaldo con contexto completo. Acotado: una sola ronda. | +1–2 llamadas al LLM por episodio |
| Solo `source_ids` obligatorios | Barato | El modelo puede citar una fuente que no dice lo que afirma |
| Bucle hasta que no haya fallos | Máxima garantía | Coste y duración no acotados |

## Consecuencias
`episode.status` alimenta a la vez la **UI de progreso en directo** ([0014](0014-ux-reproductor-inmersivo.md)), los **reintentos** y las **métricas operativas** (fallos y latencia por etapa).
