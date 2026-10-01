# 0004 · Almacenamiento de audio: volumen local en la VPS

**Estado:** Aceptada

## Contexto
Cada episodio de 10 min en MP3 a 128 kbps ocupa unos 10 MB. Lo sirven el reproductor web y las apps de podcasts vía RSS.

## Decisión
Ficheros en un volumen Docker (`/data/audio/<user>/<episode>.mp3`), servidos por FastAPI con soporte de `Range` (necesario para avanzar o retroceder en el audio). Todo el acceso pasa por una única función `save_audio()` / `audio_url()`.

## Alternativas

| Opción | Gratis | Pros | Contras |
|---|---|---|---|
| **Disco local (elegida)** | Sí | Cero dependencias. Lo más simple de explicar. | Ligado a la VPS. El ancho de banda sale de la VPS. |
| Cloudflare R2 | 10 GB/mes, **sin coste de salida** | API compatible con S3. CDN. Ideal para audio. | Otra cuenta y credenciales. URLs firmadas para episodios privados. |
| Google Cloud Storage | 5 GB solo en regiones de EE. UU. | Natural si migramos a Cloud Run | Coste de salida por descarga |
| Firebase Storage | Igual que GCS, requiere plan Blaze | Tienes cuenta | Exige tarjeta. Mismas limitaciones que GCS. |

## Retención
Un job diario del programador ([0010](0010-programacion-y-ejecucion.md)) **borra los MP3 de más de 30 días**. El episodio sigue existiendo (guion, transcripción y fuentes) marcado como `audio_expired`. Presupuesto: unos 10 GB de los 18 GB libres de la VPS compartida (~1.000 episodios).

## Consecuencias
Migrar a R2 = reimplementar `save_audio()` / `audio_url()` (unas 20 líneas con `boto3`).

## Revisar si
Movemos el backend a Cloud Run o el disco de la VPS se llena.
