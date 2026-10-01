# 11 · `feat/ask-hosts`

**Objetivo:** mientras escuchas, preguntas algo y **los presentadores te responden con su voz** en unos segundos, basándose en las fuentes del capítulo. Luego el episodio continúa.
**Depende de:** 9. **ADR:** 0014.

## Backend: `POST /episodes/{id}/ask`
- **Body** `{question: str (3–300), position_s: float}`. 404 si el episodio no es del usuario; 409 si no está `ready`; 429 si hay más de 10 preguntas por episodio y hora (se cuentan los eventos `ask_asked`).
- **Contexto:**
  - capítulo activo en `position_s` (`chapter_at(script, t)`; si es intro u outro, el más cercano con historia);
  - turnos del capítulo;
  - textos de sus artículos (`work.articles`, recortados a 4.000 caracteres cada uno);
  - título del episodio y presentadores e idioma (`prefs_snapshot`).
- **LLM** (`ASK_MODEL = gpt-5.4-mini`, prompt `prompts/ask.md`), salida `AskAnswer {turns: [{speaker, text, source_ids}]}`:
  - responder **como los presentadores**, con el mismo tono y en el idioma del episodio;
  - en dúo/debate, 2–3 turnos (uno reacciona a la pregunta y otro responde); en solo, 1 turno;
  - ≤ 450 caracteres en total;
  - solo con los artículos; si la respuesta no está en ellos, decirlo con honestidad ("nuestras fuentes no lo cuentan, pero lo que sí sabemos es…");
  - empezar reconociendo la pregunta de forma natural ("Buena pregunta, …").
- **TTS:** `text_to_dialogue.convert` (sin timestamps) → `AUDIO_DIR/<user>/<episode>/ask-<qid>.mp3` (`qid = uuid4().hex[:8]`).
- **Respuesta:** `{qid, turns, audio_url: f"{PUBLIC_BASE_URL}/audio/{id}/ask-{qid}.mp3?k={token}"}`.
- **Evento `ask_asked`:** `{question, position_s, chapter_index, latency_s, chars}`. Los créditos TTS se suman al coste del episodio.
- **Latencia objetivo:** < 8 s (LLM mini ~2–4 s + TTS de ~450 caracteres ~2–3 s).

## Frontend
- Botón **"Preguntar"** (icono de micrófono + "Pregunta a los presentadores") junto a los controles.
- **Al pulsar:**
  - el audio se pausa y se guarda la posición;
  - se abre una hoja inferior con un campo de texto y el **dictado por voz** opcional (Web Speech API `SpeechRecognition`, solo si el navegador la soporta, con el idioma del episodio);
  - chips de sugerencias: "¿Por qué importa?", "Explícamelo más simple", "¿Qué dicen otros medios?", "¿Qué pasa ahora?" (traducidos).
- **Mientras se genera:** los avatares en estado "pensando" (puntos animados y anillo en pulso) + "Pensando…".
- **Respuesta:**
  - se reproduce su audio;
  - los turnos aparecen en la transcripción como una **burbuja de preguntas y respuestas** insertada en la posición, con un estilo distinto;
  - el resaltado es por turno, aproximado por proporción de caracteres sobre la duración.
- **Al terminar:** se reanuda el episodio 2 s antes de donde se pausó. Botón "Volver al episodio" para cortar la respuesta.
- Las preguntas y respuestas de la sesión se mantienen en la transcripción hasta salir de la página.

## Commits (en orden)
1. **`feat(pipeline): chapter lookup and ask prompt`**: `chapter_at` + test; `prompts/ask.md`.
2. **`feat(api): ask the hosts endpoint`** + tests (límite de peticiones, episodio no listo, validación de la longitud de la respuesta).
3. **`feat(api): serve ask answer audio`** (ruta de audio con `qid`) + test.
4. **`feat(frontend): ask sheet with suggestions and voice dictation`**.
5. **`feat(frontend): thinking state, answer playback and resume`**.
6. **`feat(frontend): Q&A bubbles in transcript`**.

## Verificación final
- 5 preguntas reales en un episodio (una fuera de las fuentes) → respuestas fieles, en el idioma correcto, con < 8 s de latencia media y reanudación correcta.
- Dictado por voz probado en Chrome; en un navegador sin soporte, el botón del micrófono no aparece.
- `improve` sobre la hoja y la burbuja.

## Criterios de aceptación
- [ ] La respuesta suena con las voces del episodio y se reanuda donde estaba.
- [ ] Sin respuestas inventadas: si no está en las fuentes, se dice.
- [ ] Límite de peticiones activo; eventos registrados con latencia.
