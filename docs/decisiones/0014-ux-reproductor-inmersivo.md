# 0014 · UX: reproductor inmersivo

**Estado:** Aceptada

## Contexto
Prioridad nº 2: UX impresionante. Referentes: **Huxe** (la pantalla sigue a la conversación; "saltar" y "cuéntame más"), **NotebookLM** (dos presentadores naturales), **Apple Podcasts/Snipd** (transcripción sincronizada; tocar una frase lleva a ese momento), **Particle/Ground News** (una historia, varios medios), **Spotify** (pantalla completa con color dinámico e identidad), **Overcast** (velocidad y sensación de app nativa).

## Decisión (por orden de impacto/esfuerzo)
1. **Generación en directo:** pasos animados que cuentan lo que pasa ("📡 42 artículos… 🧠 El editor eligió 6… ✍️ Escribiendo… 🔎 Comprobando los hechos… 🎙️ Grabando…") vía polling (ver ADR 0010). La espera es parte del espectáculo.
2. **Reproductor a pantalla completa:**
   - avatar del presentador que habla;
   - transcripción tipo karaoke donde tocar una frase salta a ese momento;
   - **tarjeta de la historia** (imagen del artículo, logos de los medios, enlace) que aparece cuando empieza;
   - barra de capítulos;
   - 👍/👎/saltar por historia.
   Todo posible gracias a los timestamps de ElevenLabs ([0008](0008-tts.md)).
3. **Portada generativa por episodio**: degradado y patrón a partir de los temas, en CSS y sin coste. **Título creativo** generado por el guionista.
4. **Solo web app (responsive, sin app móvil ni PWA instalable).** Usamos la **Media Session API** del navegador: teclas multimedia en escritorio y controles en la pantalla de bloqueo cuando se escucha desde el navegador del móvil.
5. **Muestras de voz** al elegir presentadores (`preview_url` de ElevenLabs, gratis).
6. Velocidad 0.8–2x, modo oscuro y atajos de teclado (espacio, ←/→).

## "Pregunta a los presentadores" (en alcance, se implementa después del flujo principal)
Mientras escuchas, pulsas "Preguntar" y escribes o dices: *"¿y esto cómo afecta a España?"*. El audio se pausa. El backend manda al LLM tu pregunta junto con el guion y los artículos del capítulo actual, genera una respuesta corta con la voz de los presentadores (unos 20 s) y la reproduce. Luego el episodio continúa. Inspirado en el modo interactivo de NotebookLM y Huxe.
- **Coste:** 1 llamada al LLM + unos 400 caracteres de TTS por pregunta. Latencia de unos 5–10 s (con una animación de "pensando…").
- **Complejidad:** un endpoint (`POST /episodes/{id}/ask`) y un estado en el reproductor. La respuesta se guarda como evento (`ask`) para el dashboard.
- La versión de voz en tiempo real (interrumpir hablando) exige Realtime API y WebRTC: fuera de alcance.

## Alternativas descartadas
- Portada con IA generativa de imagen: lenta y cara por episodio, y la CSS luce casi igual.
- App nativa o PWA instalable: el producto es solo web. La Media Session API da los controles del sistema sin instalar nada.

## Revisión durante la implementación (2026-10-02 → 04)
- **Fondo:** un orbe CSS que late mientras suena, en vez de un `AnalyserNode` (evita CORS en el audio y el `AudioContext`, que Safari bloquea sin gesto).
- **Móvil:** la transcripción va debajo y los controles quedan fijos abajo, en vez de una hoja desplegable.
- **"Pregunta a los presentadores"** (rama 11): botón en la tarjeta de la historia en curso y en los controles; pausa, hoja con sugerencias, respuesta con las voces del episodio a partir de las fuentes de esa historia, y el episodio sigue 2 s antes. Sin dictado por voz (escribir o elegir una sugerencia lo cubre). **Latencia medida: 8,5–12,7 s** (más que los 5–10 s previstos; casi todo es la voz) y ~0,06–0,09 USD por respuesta. Límite de 10 por episodio y hora.
- Los 👍/👎 se guardan como eventos y el editor del siguiente episodio los tiene en cuenta; el reproductor los vuelve a mostrar al recargar.
