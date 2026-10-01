# 06 · `feat/episode-pipeline`

**Objetivo:** `generate_episode(episode_id)` produce de principio a fin un episodio `ready`: MP3 en disco, guion verificado con tiempos por turno y por palabra, costes y tiempos por etapa. Se ejecuta en el pool de hilos y es reanudable desde la etapa que falló.
**Depende de:** 5. **ADRs:** 0007, 0008, 0009, 0010, 0016.
**Es la rama más importante:** determina la calidad del `sample.mp3`.

## Estructura
```
app/llm.py              parse(model, system, user, schema) -> (obj, usage_usd, tokens)
app/audio.py            concat_mp3(paths, out), duration(path)   # ffmpeg/ffprobe
app/storage.py          episode_audio_path(user_id, ep_id), save, delete_expired()
app/pipeline/run.py     generate_episode(episode_id) + stage() + run_in_pool()
app/pipeline/editor.py  pick_stories(prefs, candidates, memory, feedback) -> EditorSelection
app/pipeline/research.py build_articles(selection, candidates) -> list[Article]
app/pipeline/writer.py  write_script(...) -> Script ; revise_script(script, issues, articles) -> Script
app/pipeline/checker.py check_script(script, articles) -> CheckerReport
app/pipeline/voice.py   record(script, hosts, lang, seed, out_dir) -> (Script con tiempos, mp3_path, chars)
app/pipeline/prompts/   editor.md writer.md checker.md
app/routers/audio.py    GET /audio/{episode_id}.mp3?k=
scripts/generate_episode_cli.py
```

## Orquestación (`run.py`)
```python
STAGES = ["fetching", "editing", "researching", "writing", "verifying", "recording"]

def generate_episode(episode_id):
    ep = load(episode_id); prefs = Preferences(**ep.prefs_snapshot)
    start = ep.failed_stage or "fetching"        # reanudación
    for name in STAGES[STAGES.index(start):]:
        with stage(ep, name):                     # status=name, commit, cronometra; si hay excepción: failed + failed_stage + error + evento
            STEP[name](ep, prefs)                 # cada paso lee y escribe ep.work[...] y hace commit
    finish(ep)                                     # status=ready, title, summary, stories, evento episode_ready
```
- Cada paso **solo** lee `ep.work` de los pasos previos y escribe su propia clave: `candidates`, `selection`, `articles`, `draft_script`, `checker_report`, `final_script`. Así el reintento es trivial.
- `run_in_pool(episode_id)`: `executor.submit(generate_episode, episode_id)`. El executor vive en `jobs.py` (se crea en el `lifespan`). Esta rama crea `jobs.py` solo con el executor; el programador llega en la rama 10.
- **Al arrancar:** los episodios con `status` no terminal → `failed_stage = status` y se reenvían al pool (recuperación tras un reinicio).
- `EPISODE_MAX_MINUTES` limita `duration_min` efectivo: `minutes = min(prefs.duration_min, settings.episode_max_minutes)`.

## Presupuestos por duración

| Minutos | Historias | Caracteres hablados aprox. (≈900/min) | Peticiones TTS (≤1.800 car.) |
|---|---|---|---|
| 2 (desarrollo) | 2 | 1.800 | 1–2 |
| 5 | 3 | 4.500 | 3 |
| 10 | 5 | 9.000 | 5–6 |
| 20 | 7 | 18.000 | 10–11 |

Fórmula en el código: `stories = {2:2, 5:3, 10:5, 20:7}[minutes]` y `target_chars = minutes * 900`. El guionista recibe ambos valores. Se acepta ±15 %; si el guion se pasa más de un 30 %, se recortan los turnos de menor prioridad (los de cierre de cada capítulo).

## Paso 1 · Reportero (`fetching`)
`gather_candidates(prefs, since)` (rama 5) → `work.candidates`. Si hay menos de 5 candidatos → error legible: "No encontramos noticias recientes sobre tus intereses".

## Paso 2 · Editor (`editing`) — `gpt-5.4-mini`
**Entrada (JSON en el mensaje de usuario):**
- intereses con peso;
- `avoid` y `sources_i_trust`;
- `depth`;
- número de historias;
- candidatos (id, título, medio, fecha, extracto ≤ 300 caracteres, interés);
- **memoria:** historias de `stories` de los últimos 14 días (título, resumen, fecha);
- **feedback por interés:** 👍, 👎 y saltos de los últimos 30 días (`feedback_by_interest(user_id)`: une `events` de tipo `feedback`/`chapter_skipped` con `episodes.work.selection` para mapear `story_id → interest`).

**Reglas del prompt `editor.md`:**
1. Elegir exactamente N historias + 2 de reserva (`backups`), priorizando novedad, importancia y peso del interés.
2. Agrupar en una misma historia los candidatos que cuentan lo mismo (varios medios).
3. No repetir historias de la memoria **salvo novedad sustancial**; entonces marcar `follow_up_of`.
4. Diversidad: no más de 2 historias del mismo interés salvo que solo haya uno.
5. Preferir los medios de `sources_i_trust`; nunca historias que encajen en `avoid`.
6. Penalizar los intereses con más 👎 o saltos; reforzar los que tienen 👍.

**Salida:** `EditorSelection` (añadir `backups: list[EditorPick]` al contrato). Validación: ids existentes y ningún candidato repetido entre historias.

## Paso 3 · Documentación (`researching`)
Para cada historia (más las reservas si hace falta): hasta **2 artículos de medios distintos** con `get_article()` (rama 5). El candidato de Exa ya trae `text` (si es suficientemente largo).
- Una historia necesita ≥ 1 artículo con más de 800 caracteres; si no lo consigue, se sustituye por una reserva.
- Si al final hay menos historias de las pedidas, se continúa con las que haya (mínimo 2) y se registra en `work`.
- Salida: `work.articles` (`Article` con ids `a1..aN`, `text[:6000]`, `image_url`).

## Paso 4 · Guionista (`writing`) — `gpt-5.4`
**Entrada:** preferencias (formato, tono, profundidad, idioma, nombres de los presentadores, nombre del oyente si existe), historias + artículos, `target_chars`, seguimientos, fecha de hoy y día de la semana.

**Reglas del prompt `writer.md`** (claves para la calidad):
1. **Idioma:** todo en `language`, aunque las fuentes estén en otro.
2. **Estructura:** capítulo de intro (saludo personal, titulares de lo que viene en una frase cada uno) → un capítulo por historia → outro (resumen de 1 frase + despedida + "nos oímos mañana" según la frecuencia).
3. **Formatos:**
   - `solo`: un presentador; turnos más largos.
   - `duo`: conversación natural, con interrupciones breves ("¡espera!", "¿en serio?"), alternancia y un presentador que explica mientras el otro pregunta lo que preguntaría el oyente.
   - `debate`: cada historia con un punto a favor y otro en contra, y un cierre equilibrado.
4. **Hechos:** solo lo que dicen los artículos aportados. Cada turno con afirmaciones lleva sus `source_ids`. Citar el medio de forma natural ("según El País…"). Nada de cifras ni citas inventadas. Si los medios discrepan, decirlo.
5. **Seguimientos:** "Como os contamos el martes, … hoy hay novedades: …".
6. **Para TTS:**
   - turnos ≤ 600 caracteres;
   - números y siglas escritos como se dicen ("tres mil millones");
   - sin URLs, markdown ni emojis;
   - etiquetas de audio v3 con moderación (máximo 1 cada 3 turnos), solo de esta lista: `[laughs]`, `[chuckles]`, `[sighs]`, `[curious]`, `[excited]`, `[surprised]`, `[thoughtful]`, `[serious]`, `[whispers]`, `[pause]`.
7. **Longitud:** `target_chars ±15 %` contando solo el texto hablado.
8. **Título** creativo (≤ 70 caracteres) y **summary** (≤ 280 caracteres) para el RSS.

**Salida:** `Script` → `work.draft_script`.

## Paso 5 · Verificador (`verifying`) — `gpt-5.4`
1. `check_script(draft, articles)`: el prompt `checker.md` recibe cada turno con sus `source_ids` y el texto de esos artículos; marca los turnos `unsupported | exaggerated | misattributed | outdated` con una explicación. Los turnos sin `source_ids` (intro, transiciones) solo se revisan si afirman hechos.
2. Si `verdict == "fix"` → `revise_script(draft, issues, articles)` (`gpt-5.4`, mismo prompt del guionista + "corrige SOLO estos turnos; mantén el resto idéntico").
3. Segunda comprobación sobre el guion revisado; los turnos que sigan marcados **se eliminan** (si un capítulo se queda sin turnos con hechos, se elimina el capítulo entero).
4. `work.checker_report = {first: …, second: …, issues_found, issues_fixed, turns_removed}` → `work.final_script`.

Máximo 2 llamadas al verificador y 1 reescritura: coste y duración acotados.

## Paso 6 · Locutores (`recording`) — ElevenLabs
1. **Troceado** (`chunk_turns`): por capítulo, agrupar turnos consecutivos en tramos de ≤ 1.800 caracteres **sin partir turnos**. Función pura, con test.
2. Por tramo: `client.text_to_dialogue.convert_with_timestamps(inputs=[DialogueInput(text, voice_id=hosts[speaker].voice_id)…], model_id="eleven_v3", output_format="mp3_44100_128", language_code=lang, seed=episode_seed)` → se guarda `chunk_{i}.mp3` en una carpeta temporal.
   - Continuidad: probar `previous_text`/`previous_request_ids`. Si `eleven_v3` no los acepta, no se usan; anotarlo en el ADR 0008.
   - Reintento con *backoff* (3 intentos) ante 429/5xx.
3. **Tiempos:**
   - `offset` acumulado = suma de `ffprobe duration(chunk_j)` de los tramos anteriores. Usar la duración real del MP3, **no** `end_time_seconds` del último segmento: medido, cada tramo trae ~1,2 s de silencio final.
   - Para cada `voice_segment`: `dialogue_input_index` → turno; `turn.start_s = offset + min(start)`, `turn.end_s = offset + max(end)`.
   - **Palabras:** con `alignment` (caracteres y tiempos) y `character_start/end_index` de cada segmento, se reconstruye el texto de cada turno y se parte en palabras → `turn.words = [[start_s, "palabra"], …]` (las etiquetas `[…]` se excluyen). Si el texto alineado no cuadra con el del turno (normalización), `words = None` y el reproductor resalta por turno.
   - `chapter.start_s` y `end_s` a partir de sus turnos.
4. **Montaje:** `concat_mp3(chunks, out)` con `ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp3`. Medido el 2026-10-01: la concatenación binaria deja una cabecera Info/Xing con la duración del primer tramo (3,87 s de 7,2 s), mientras que ffmpeg reescribe la cabecera (7,26 s) y el audio decodifica limpio. Después `duration_s = ffprobe(out)`.
5. Guardar en `AUDIO_DIR/<user_id>/<episode_id>.mp3`; `tts_chars = Σ len(text)`.

## Finalizar
`status=ready`; `title`, `summary` y `script` (el final con tiempos); `duration_s`, `cost` y `stage_timings`; `finished_at`. Se crean las filas de `stories` (una por capítulo con `story_id`) y el evento `episode_ready` con props.

## Audio (`routers/audio.py`)
`GET /audio/{episode_id}.mp3?k=<feed_token>` → 404 si no existe o el token no es del dueño; 410 si `audio_expired`. Con `FileResponse(path, media_type="audio/mpeg")`. **Verificar que Starlette responde 206 a `Range: bytes=0-1`** (test); si no lo hace, implementar el rango a mano (unas 20 líneas).

## Costes (`llm.py`)
`PRICES = {"gpt-5.4": (in_per_1M, out_per_1M), "gpt-5.4-mini": (…)}`, rellenado con la página de precios de OpenAI al implementar. `parse()` devuelve el uso; `run.py` suma en `ep.cost`. TTS: créditos = caracteres.

## Commits (en orden)
1. **`feat(llm): structured-output wrapper with cost accounting`**: + test de cálculo de coste.
2. **`feat(audio): ffmpeg concat and ffprobe duration`**: + test que genera dos MP3 de 1 s con `ffmpeg -f lavfi -i sine` y comprueba que la duración concatenada es ≈ 2 s.
3. **`feat(storage): audio paths and save`**.
4. **`feat(pipeline): stage runner with status, timings and resume`**: `run.py` con los pasos simulados; test: un paso que falla deja `failed` + `failed_stage`, y el reintento empieza en esa etapa.
5. **`feat(pipeline): editor step and prompt`**: + test de validación de la selección (ids inexistentes o duplicados → error).
6. **`feat(pipeline): research step`**: sustitución por reservas; test con `get_article` inyectado.
7. **`feat(pipeline): writer step and prompt`**.
8. **`feat(pipeline): fact-checker with one revision round`**: test de la lógica de "eliminar turnos que siguen marcados" y del recuento de issues.
9. **`feat(pipeline): voice step with chunking and timeline`**: tests de `chunk_turns`, `build_timeline` (segmentos y duraciones sintéticos) y `words_from_alignment` (alineación sintética).
10. **`feat(api): signed audio endpoint`**: + test de 206 con `Range`.
11. **`chore(scripts): generate_episode_cli`**: `--prefs scripts/sample_prefs.json --minutes 2 [--resume <episode_id>]`. Crea un usuario CLI si no existe, ejecuta de forma síncrona e imprime los tiempos por etapa, el coste, la ruta del MP3 y el resumen del verificador.
12. **`feat(pipeline): startup recovery of interrupted episodes`**.

## Verificación final
- `pytest` en verde (sin red).
- **3 episodios reales de 2 min** con el CLI (es y en, formatos `duo` y `solo`): escuchar completos. Comprobar:
  - los hechos coinciden con las fuentes (muestreo manual de 5 turnos);
  - los tiempos de turno y palabra coinciden con el audio (abrir en un reproductor y contrastar 3 puntos);
  - la duración del MP3 en Chrome y Safari es la real.
- Matar el proceso a mitad de `recording` → al reiniciar se reanuda y termina.
- Coste anotado de cada episodio en `docs/plans/06-resultados.md` (tokens, USD y créditos).
- Revisión con `thermo-nuclear-code-quality-review`.

## Criterios de aceptación
- [ ] Un episodio de 2 min se genera en < 3 min y queda `ready` con el audio reproducible.
- [ ] El verificador registra los issues y el guion final no contiene turnos marcados.
- [ ] El reintento tras un fallo reutiliza el trabajo previo (no vuelve a llamar al editor si el fallo fue en `recording`).
- [ ] `work`, `cost` y `stage_timings` quedan completos para el dashboard.

## Riesgos
- **Calidad del guion:** es el factor nº 1 → iterar los prompts con episodios de 2 min antes de gastar en uno de 10. Guardar cada versión del prompt en git.
- **Créditos de ElevenLabs:** cada prueba de 2 min ≈ 1.800 créditos → presupuestar unas 10 pruebas (18k) + el `sample.mp3` final de 10 min (9k).
- **Saltos de tono entre tramos:** `seed` fijo + cortes en el límite de capítulo (no a mitad de conversación) + continuidad si `eleven_v3` la admite.
- **Etiquetas de audio en la alineación:** pueden desalinear las palabras → *fallback* a resaltar por turno.
