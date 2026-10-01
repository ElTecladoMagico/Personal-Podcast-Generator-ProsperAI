# 08 · `feat/onboarding`

**Objetivo:** en menos de 60 segundos, un usuario nuevo define qué le interesa y cómo quiere su podcast (o lo **importa desde su IA**) y sale con su primer episodio en producción.
**Depende de:** 2, 6. **ADRs:** 0012, 0014, 0015.

## Backend
- **`PUT /me/preferences`:**
  - valida `Preferences`: 1–12 intereses; `hosts` = 1 si `solo` y 2 si `duo`/`debate`; voces del catálogo; zona horaria válida (`zoneinfo`);
  - guarda y recalcula `next_run_at = compute_next_run(schedule, now_utc)`;
  - body `{preferences, method}`: la primera vez rellena `onboarded_at` y registra `onboarding_completed` con `{"method": method}`; después, `preferences_updated`.
- **`compute_next_run(schedule, now, lead_min=GENERATION_LEAD_MIN) -> datetime | None`** en `app/schedule.py` (devuelve la ocurrencia menos `lead_min`; si ese instante ya pasó, la siguiente ocurrencia):
  - `off` → None;
  - `daily` → próxima ocurrencia de `time` en la zona horaria;
  - `weekdays` → la siguiente de lunes a viernes;
  - `weekly` → el siguiente `weekday`.
  - Resultado en UTC. Tests: cambio de hora (DST) en Europe/Madrid, cruce de medianoche, fin de semana, antelación que cae en el pasado.
- **`POST /me/preferences/import`** con `{text}`:
  - `extract_json(text)`: quita los bloques ``` ``` y busca el primer objeto `{…}` balanceado (respetando las cadenas), luego `json.loads`;
  - valida con `ImportedPreferences` (todos los campos opcionales salvo `interests`): pesos acotados a 1–5, máximo 12 intereses, se descartan campos desconocidos;
  - si falla, 422 con un mensaje útil ("No encontramos un JSON válido. ¿Copiaste la respuesta completa?").
  - Tests con 8 entradas reales y "sucias": con texto alrededor, con ```json, con comas finales (→ error claro), con campos extra, vacía…
- **`GET /voices`:** catálogo con `{id, name, descriptor, preview: {en: "/voices/<id>-en.mp3", es: "/voices/<id>-es.mp3"}}`.

## Prompt "Importar desde tu IA" (constante en el frontend, en EN y ES)
Debe funcionar en ChatGPT, Claude y Gemini, tengan o no memoria del usuario:
```
I'm setting up a personal daily news podcast. Using everything you know about me
(memory, past conversations), describe my interests. If you don't know enough,
ask me up to 3 quick questions first, then answer.
Reply with ONLY this JSON, no extra text:
{"interests":[{"topic":"<specific topic, e.g. 'EU AI regulation' not 'tech'>","why":"<one line>","weight":<1-5>}],
 "avoid":["<topics I dislike>"],
 "sources_i_trust":["<outlets>"],
 "language":"<ISO 639-1 of the language I speak with you>",
 "tone":"casual|serious|nerdy",
 "depth":"headlines|analysis"}
Give 5-10 interests, as specific as possible.
```

## Frontend: asistente a pantalla completa (`/onboarding`)
Una pregunta por pantalla, indicador de progreso, transiciones con `motion`, se puede volver atrás y el estado se conserva en memoria.
1. **"¿Qué te interesa?"**, con tres caminos:
   - **Importar desde tu IA** (destacado): diálogo con "Copiar prompt" (portapapeles + toast), enlaces "Abrir ChatGPT / Claude", un `textarea` para pegar y "Importar". Los intereses **aparecen volando como chips** (*stagger*).
   - **Sugerencias:** chips por categoría (Tecnología, Economía, Deportes, Ciencia, Cultura, Política, Salud…) con subtemas concretos.
   - **Texto libre:** "Añadir tema" con Enter.
   - Cada chip tiene un peso (1–5, puntos visibles y popover con slider) y una ✕.
2. **"¿Algo que prefieras evitar?"** + "Medios de confianza" (opcional, "Saltar").
3. **"¿Cómo quieres que suene?"**: tarjetas de formato (Solo / Dúo / Debate, con mini ilustración y una línea de ejemplo), tono, profundidad y duración (5/10/20).
4. **"Conoce a tus presentadores"**: tarjetas de voz con ▶ (muestra pregenerada en ES o EN; para otros idiomas se usa la EN con la nota "también habla <idioma>"), nombre editable y selección de 1 o 2 según el formato. Pareja por defecto: Sarah + George.
5. **"Idioma y horario"**: idioma del podcast; frecuencia (diaria, laborables, semanal, solo a demanda); hora; zona horaria detectada con `Intl.DateTimeFormat().resolvedOptions().timeZone` y editable.
6. **Final:** `PUT /me/preferences` → `POST /episodes` (primer episodio automático) → `Home` mostrando `GenerationProgress`. Copia: "Tu redacción ya está trabajando en tu primer episodio".

**`/settings`:** las mismas secciones como formulario normal (no asistente), guardado con toast. El feed RSS llega en la rama 10.

## Script `scripts/voice_previews.py`
Para cada voz × {en, es}: TTS `eleven_v3` con la frase "Hi, I'm {name}. This is your personal news podcast — made just for you." (y su versión en ES) → `frontend/public/voices/{id}-{lang}.mp3`. Unos 24 × 70 = ~1.700 créditos, **una sola vez**; los MP3 se versionan (~30 KB cada uno). Rellenar los `descriptor` del catálogo escuchándolas.

## Commits (en orden)
1. **`feat(backend): schedule next-run computation`** + tests.
2. **`feat(api): save preferences`** + tests de validación.
3. **`feat(api): import preferences from pasted AI output`** + tests de `extract_json`.
4. **`feat(api): voices catalog endpoint`**.
5. **`chore(scripts): generate voice previews`** + los MP3 generados + descriptores.
6. **`feat(frontend): onboarding wizard shell and navigation`**.
7. **`feat(frontend): interests step with AI import and chips`**.
8. **`feat(frontend): avoid, style and hosts steps`**.
9. **`feat(frontend): language and schedule step, finish and first episode`**.
10. **`feat(frontend): settings page`**.

## Verificación final
- Usuario nuevo en local: importar con una respuesta real de ChatGPT y de Claude → chips correctos → completar → primer episodio en producción.
- Recorrido manual sin importar → igual de fluido.
- Cambiar la hora en ajustes → `next_run_at` correcto en la BD (comprobar en UTC).
- Revisión visual 1440/390 + revisión de diseño (`ecc:frontend-design-direction` + Lighthouse); navegación con teclado por todo el asistente.

## Criterios de aceptación
- [ ] La importación tolera las respuestas "sucias" típicas y da errores comprensibles.
- [ ] El asistente se completa en < 60 s con importación.
- [ ] Las preferencias guardadas validan contra `Preferences` y el primer episodio arranca solo.
