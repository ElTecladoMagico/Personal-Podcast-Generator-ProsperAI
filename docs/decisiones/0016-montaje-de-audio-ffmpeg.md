# 0016 · Montaje de audio con ffmpeg

**Estado:** Aceptada (revisa la simplificación "sin ffmpeg" de los ADRs 0008 y 0009)

## Contexto
El episodio se graba en varios tramos (ElevenLabs admite ~2.000 caracteres por petición) que hay que unir en un único MP3. Habíamos supuesto que bastaba con concatenar los bytes.

## Evidencia (prueba del 2026-10-01 con dos tramos reales de `eleven_v3`)

| Método | Duración en la cabecera Info/Xing | Decodificación |
|---|---|---|
| `cat p1.mp3 p2.mp3` | **3,87 s** (la del primer tramo; real: ~7,2 s) | Error "Header missing" en la unión |
| `ffmpeg -f concat -c copy` | **7,26 s** (correcta) | Limpia |

Los navegadores usan esa cabecera para mostrar la duración y saltar dentro del audio: con la concatenación binaria, la barra de progreso y el *seek* estarían mal.

## Decisión
Incluir `ffmpeg` en la imagen Docker (`apt-get install ffmpeg`, ~80 MB) y usar:
- `ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp3` para unir sin recodificar (rápido y sin pérdida);
- `ffprobe -show_entries format=duration` para medir cada tramo y calcular los desplazamientos de los tiempos.

Todo vive en `app/audio.py` (2 funciones, unas 30 líneas).

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **ffmpeg concat (elegida)** | Correcto, estándar, una línea | Dependencia del sistema (~80 MB en la imagen) |
| Concatenación binaria | Cero dependencias | Duración y *seek* incorrectos (medido) |
| Quitar a mano la trama Info/Xing de cada tramo | Python puro | Lógica binaria de MPEG frágil y difícil de explicar |
| `pydub` | API cómoda | Usa ffmpeg igualmente y recodifica |
| Pedir PCM y codificar nosotros | Control total | PCM 44,1 kHz exige el plan Pro; igualmente necesita un codificador |

## Consecuencias
Con ffmpeg disponible se abren mejoras baratas para el futuro (normalización de volumen `loudnorm`, sintonía de entrada); no entran en el alcance actual (YAGNI).

## Revisión (2026-10-04): pausas entre capítulos y volumen igualado
Al escuchar `sample.mp3`, los cambios de tema eran bruscos y la voz parecía cambiar un poco. Medido sobre el audio:
- entre turnos de un mismo capítulo había una pausa natural de ~0,7 s (mediana), pero **en los cambios de capítulo ≤ 0,27 s o ninguna**: cada trozo de ElevenLabs llega sin silencio en los bordes y se unían pegados;
- cada capítulo es una petición distinta y, en modo *creative*, el volumen de una voz variaba **el doble entre capítulos que dentro de uno** (1,5 dB frente a 0,76 dB; la otra voz, 0,4 dB).

Ahora `audio.assemble` hace en **un solo paso de ffmpeg**: `loudnorm` de cada trozo a −16 LUFS (estándar de podcast), una pausa después (0,9 s antes de un capítulo nuevo, 0,35 s si un capítulo largo se partió), la unión y el ×1,1, con una sola codificación. La pausa cuenta en la duración del trozo, así que la transcripción sigue sincronizada. Sin coste extra de ElevenLabs. `concat_mp3` desaparece.

Queda (decisión de producto): el timbre sigue variando algo entre peticiones con `stability = 0.0`; con 0,5 (*natural*) varía menos pero suena menos viva (ver la prueba A/B del [0008](0008-tts.md)).
