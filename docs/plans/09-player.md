# 09 · `feat/player`

**Objetivo:** el reproductor inmersivo de `/episodes/:id` —el corazón de la UX— y la instrumentación que alimenta la personalización y el dashboard.
**Depende de:** 7. **ADRs:** 0013, 0014.

## Datos (ya disponibles por la rama 7)
`GET /episodes/{id}` → `script` (capítulos → turnos → `start_s`, `end_s`, `words`), `sources` (`a1 → {title, url, source, image_url}`), `audio_url`, `duration_s` y `prefs_snapshot.hosts` (nombres).

## Composición
- **Escritorio:**
  - columna izquierda: portada grande, título, presentadores con sus avatares y los controles;
  - columna derecha: transcripción viva;
  - encima de la portada: la **tarjeta de la historia** actual.
- **Móvil:** portada y controles arriba; transcripción en una hoja inferior desplegable.
- **Fondo:** gradiente difuminado con los colores de la portada, con un **orbe reactivo al audio** detrás de los avatares (Web Audio `AnalyserNode`).

## Componentes y lógica
- **`useAudio(src)`** (hook propio, sin librerías):
  - `HTMLAudioElement` con `crossOrigin="anonymous"` (para el `AnalyserNode`; el CORS del backend ya cubre `/audio`);
  - estado `playing`, `currentTime` (con `requestAnimationFrame` mientras suena), `duration`, `rate`;
  - acciones `play`, `pause`, `seek(t)`, `setRate(r)`.
- **`lib/timeline.ts`** (funciones puras, testeadas con `vitest`):
  - `findActive(items, t)` (búsqueda binaria por `start_s`);
  - `activeChapter(script, t)`, `activeTurn(...)`, `activeWord(turn, t)`;
  - `chapterSegments(script, duration)` (anchos de la barra de capítulos).
- **Transcripción viva:**
  - turnos con el avatar y el nombre del presentador;
  - la palabra actual resaltada (o el turno, si `words == null`);
  - pulsar una palabra o un turno hace `seek`;
  - autoscroll que mantiene el turno activo centrado, pausado 4 s si el usuario hace scroll a mano;
  - las etiquetas `[laughs]` no se muestran;
  - los `source_ids` aparecen como superíndices clicables que abren la fuente.
- **Avatares de los presentadores:** iniciales con el color de cada uno; un anillo animado en quien habla (según `turn.speaker`) y escala sutil con la amplitud del analizador.
- **Tarjeta de la historia:** al cambiar de capítulo, entra con `motion`:
  - imagen (`image_url` del primer artículo con imagen; si no hay, la portada) y titular;
  - logos de los medios (favicon `https://www.google.com/s2/favicons?domain=<host>&sz=64`) y "Leer en …";
  - acciones **👍 / 👎** (estado guardado localmente para el capítulo) y **"Saltar historia"** (seek al inicio del siguiente capítulo).
- **Barra de capítulos:** progreso segmentado por capítulo con el título al pasar el ratón; pulsar hace `seek` al inicio.
- **Controles:** play/pausa grande, −15 s / +30 s, velocidad (0.8 · 1 · 1.25 · 1.5 · 2), tiempo actual/total.
  - Atajos: `Espacio` play/pausa, `←/→` ±5 s, `Shift+←/→` capítulo anterior/siguiente.
- **Media Session API:** `MediaMetadata({title, artist: "Personal Podcast", album: fecha, artwork: [portada renderizada a canvas → dataURL]})`; handlers `play`, `pause`, `seekbackward`, `seekforward`, `previoustrack`/`nexttrack` (capítulos) y `seekto`; `setPositionState` al cambiar el tiempo.
- **Estados:**
  - episodio no `ready` → `GenerationProgress` (rama 7);
  - `audio_expired` → transcripción y fuentes con el aviso "El audio de este episodio ya no está disponible (más de 30 días)";
  - error de red → reintentar.
- **Accesibilidad:** controles con `aria-label`, la transcripción es una lista navegable y el orbe y las animaciones respetan `prefers-reduced-motion`.

## Instrumentación
- **Backend `POST /events`:**
  - valida `type` contra la lista del frontend en §8 del contrato (`play_started`, `chapter_started`, `chapter_skipped`, `listen_progress`, `feedback`) y que `episode_id` sea del usuario;
  - `props` con un tamaño máximo de 2 KB.
- **Frontend `useTrack(episodeId)`:**
  - `play_started` (primer play de la sesión);
  - `chapter_started` (cambio de capítulo mientras suena);
  - `chapter_skipped` (botón "Saltar" o seek hacia delante que se salta más del 50 % del capítulo);
  - `feedback`;
  - `listen_progress` con `max_position_s` al pausar, al terminar (`ended`), cada 60 s mientras suena y en `visibilitychange → hidden` (`fetch` con `keepalive: true`).

## Commits (en orden)
1. **`feat(api): events ingestion endpoint`** + tests (tipo no permitido, episodio ajeno, props demasiado grandes).
2. **`chore(frontend): add vitest and timeline helpers`** + tests.
3. **`feat(frontend): useAudio hook and player controls`**.
4. **`feat(frontend): live transcript with word highlighting and seek`**.
5. **`feat(frontend): chapter bar and story cards with feedback and skip`**.
6. **`feat(frontend): host avatars and audio-reactive background`**.
7. **`feat(frontend): keyboard shortcuts and Media Session`**.
8. **`feat(frontend): listening analytics events`**.
9. **`feat(frontend): expired and error states`**.

## Verificación final
- Con un episodio real de 2 min:
  - la palabra resaltada coincide con lo que se oye (±0,3 s) en 3 puntos;
  - el seek por palabra funciona y los capítulos y tarjetas cambian en el momento correcto;
  - los controles del sistema funcionan: teclas multimedia del Mac y pantalla de bloqueo del móvil con Safari/Chrome.
- La tabla `events` registra la secuencia esperada de una escucha completa con un salto y un 👍.
- Chrome, Safari y Firefox; 1440/390; `improve` + `thermo-nuclear-code-quality-review`.

## Criterios de aceptación
- [ ] Transcripción sincronizada a nivel de palabra (o turno como *fallback*) sin tirones a 60 fps.
- [ ] Feedback y saltos persisten como eventos y los usa el editor del siguiente episodio (rama 6 ya lo lee).
- [ ] Reproducción correcta en móvil desde el navegador.

## Riesgos
- **`AnalyserNode` + CORS:** si el audio no tiene CORS, el analizador da ceros → verificar las cabeceras en `/audio`; *fallback*: animación procedural sin analizador.
- **Rendimiento:** re-renderizar la transcripción a 60 fps → separar el componente de la palabra activa y memoizar los turnos.
