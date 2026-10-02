# 06b · Voz en español de España (2026-10-02)

**Petición del autor:** tras escuchar los primeros episodios, "mejorar la naturalidad de la voz": español de **España**, natural e interesante, y a ser posible **un poco más rápido**.

## Qué se probó
Un único guion de 2 min (español, `duo`), con el prompt nuevo del guionista (castellano coloquial y apartado "Sounding natural"), grabado así:

| Variante | Voces | `stability` | Velocidad | Duración |
|---|---|---|---|---|
| Referencia anterior | Sarah + George (*premade*, anglosajonas) | 0,5 | ×1,0 | 119 s (otro guion) |
| `spain_natural` | Sara Martin 3 + Martin Osborne 6 (castellanas) | 0,5 *natural* | ×1,0 | 122 s |
| `spain_natural_x1.1` / `x1.15` | ídem | 0,5 | ×1,1 / ×1,15 | 111 / 106 s |
| `spain_creative` | ídem | 0,0 *creative* | ×1,0 | 118 s |
| **`spain_creative_x1.1` (elegida)** | ídem | **0,0** | **×1,1** | **107 s** |
| `spain_creative_x1.15` | ídem | 0,0 | ×1,15 | 102 s |

**Elegida por el autor, escuchando:** voces castellanas + *creative* + ×1,1: "suena más natural y viva". Coste del experimento: ~3.600 créditos (las variantes aceleradas no gastan).

## Cómo se encontraron las voces
La key no tiene `voices_read`, así que no puede listar ni buscar en la biblioteca. Los ids salen del JSON público de la página de ElevenLabs "Spanish Castilian accent" (categoría, descripción y muestra de cada voz); se comprobó que la key puede **usarlas por id** en `text_to_dialogue` sin añadirlas a una cuenta.

## Cambios
- `voice.py`: `STABILITY = 0.0` y `SPEED = 1.1`. `text_to_dialogue` solo admite `stability` y `similarity` (no `speed`), así que tras unir los tramos se aplica `ffmpeg atempo=1.1` (cambia el ritmo, no el tono) y `build_timeline(..., speed)` divide todos los tiempos para que el karaoke siga cuadrando.
- `writer.md`: "`es` = español de España" (vosotros, "vale", "o sea", vocabulario de España; nada de "ustedes", "ahorita", "computadora"…) y un apartado de naturalidad (réplicas cortas, reacciones, una muletilla como mucho, sin conectores de texto escrito, pocas cifras).
- `writer.py`: `CHARS_PER_MINUTE = 1000` (medido: *creative* habla más deprisa, ~912 car./min a ×1,0, y ×1,1 lo lleva a ~1.000).
- Voces por defecto según idioma: `es` → Sara + Martín; resto → Sarah + George (contrato §9; el catálogo llega en la rama 8).

## Riesgo
*Creative* es la estabilidad más expresiva y, según ElevenLabs, la que más puede desviarse del texto. La alineación lo detecta: si el texto alineado no coincide con el del turno, se resalta por turno en vez de por palabra.
