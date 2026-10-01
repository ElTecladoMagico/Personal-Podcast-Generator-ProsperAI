# 0014 · UX: reproductor inmersivo

**Estado:** Propuesta

## Contexto
Prioridad nº 2: UX impresionante. Referentes: **Huxe** (la pantalla sigue a la conversación; "saltar" y "cuéntame más"), **NotebookLM** (dos presentadores naturales), **Apple Podcasts/Snipd** (transcripción sincronizada; tocar una frase lleva a ese momento), **Particle/Ground News** (una historia, varios medios), **Spotify** (pantalla completa con color dinámico e identidad), **Overcast** (velocidad y sensación de app nativa).

## Decisión (por orden de impacto/esfuerzo)
1. **Generación en directo:** pasos animados que cuentan lo que pasa ("📡 42 artículos… 🧠 El editor eligió 6… ✍️ Escribiendo… 🎙️ Grabando…") vía SSE. La espera es parte del espectáculo.
2. **Reproductor a pantalla completa:**
   - avatar del presentador que habla;
   - transcripción tipo karaoke donde tocar una frase salta a ese momento;
   - **tarjeta de la historia** (imagen del artículo, logos de los medios, enlace) que aparece cuando empieza;
   - barra de capítulos;
   - 👍/👎/saltar por historia.
   Todo posible gracias a los timestamps de ElevenLabs ([0008](0008-tts.md)).
3. **Portada generativa por episodio**: degradado y patrón a partir de los temas, en CSS y sin coste. **Título creativo** generado por el guionista.
4. **PWA instalable** + **Media Session API**: controles en la pantalla de bloqueo y en los auriculares.
5. **Muestras de voz** al elegir presentadores (`preview_url` de ElevenLabs, gratis).
6. Velocidad 0.8–2x, modo oscuro y atajos de teclado (espacio, ←/→).

## Opcional: "Pregunta a los presentadores"
Mientras escuchas, pulsas "Preguntar" y escribes o dices: *"¿y esto cómo afecta a España?"*. El audio se pausa. El backend manda al LLM tu pregunta junto con el guion y los artículos del capítulo actual, genera una respuesta corta con la voz de los presentadores (unos 20 s) y la reproduce. Luego el episodio continúa. Inspirado en el modo interactivo de NotebookLM y Huxe.
- **Coste:** 1 llamada al LLM + unos 400 caracteres de TTS por pregunta. Latencia de unos 5–10 s (con una animación de "pensando…").
- **Complejidad:** un endpoint y un estado en el reproductor. **Solo si sobra tiempo.**
- La versión de voz en tiempo real (interrumpir hablando) exige Realtime API y WebRTC: fuera de alcance.

## Alternativas descartadas
- Portada con IA generativa de imagen: lenta y cara por episodio, y la CSS luce casi igual.
- App nativa: la PWA da el 90 % por el 10 % del coste.
