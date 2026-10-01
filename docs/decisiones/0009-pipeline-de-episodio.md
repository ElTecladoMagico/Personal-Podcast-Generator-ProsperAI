# 0009 · Pipeline del episodio: una "redacción" en 5 pasos

**Estado:** Propuesta

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
| 5 | Locutores | ElevenLabs por capítulo → MP3 + tiempos ([0008](0008-tts.md)) | `recording` → `ready` |

Si falla, `failed` con la etapa y el error. El reintento rehace desde la etapa fallida porque los resultados intermedios se guardan en el episodio.

**Memoria y seguimientos:** al terminar, cada historia se guarda en `stories` (título y resumen). El editor recibe las de los últimos 14 días: no las repite salvo que haya novedad, y en ese caso el guionista dice "como os contamos el martes…".

## Alternativas descartadas

| Opción | Por qué no |
|---|---|
| Deduplicación y ranking con embeddings + clustering | Más código, más conceptos (vectores, umbrales). El editor LLM hace lo mismo y se explica en una frase. |
| Paso de verificación de hechos con otro LLM | Duplica coste y latencia. Lo cubrimos con `source_ids` obligatorios y "usa solo los artículos dados". |
| Framework de agentes (LangGraph, CrewAI) | Abstracción innecesaria para 5 pasos secuenciales |
| Cola de tareas por etapa | Ver [0010](0010-programacion-y-ejecucion.md) |

## Consecuencias
`episode.status` alimenta a la vez la **UI de progreso en directo** ([0014](0014-ux-reproductor-inmersivo.md)), los **reintentos** y las **métricas operativas** (fallos y latencia por etapa).
