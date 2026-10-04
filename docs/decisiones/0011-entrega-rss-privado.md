# 0011 · Entrega: feed RSS privado por usuario

**Estado:** Aceptada

## Contexto
"On a given schedule" se cumple de verdad si el episodio **llega solo** al usuario, sin tener que abrir nuestra web.

## Decisión
Cada usuario tiene `GET /feeds/<token>.xml`: un RSS de podcast estándar (etiquetas de iTunes, `enclosure` MP3 y notas con las fuentes). Se puede suscribir desde Apple Podcasts, Pocket Casts o cualquier app que acepte "añadir por URL". El token es aleatorio (32 bytes), se puede regenerar y revocar desde la UI, y también firma las URLs de audio de ese feed.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **RSS privado (elegida)** | Estándar abierto. Funciona en cualquier app de podcasts. Unas 40 líneas. | Quien tenga la URL puede escuchar (igual que los feeds privados de Patreon o Supercast). Mitigado con token revocable. |
| Push o email al estar listo | Aviso inmediato | Requiere un proveedor de email o push. No reproduce en la app de podcasts. |
| Solo reproductor web | Lo más simple | El usuario tiene que acordarse de entrar |

## Consecuencias
Las apps de podcasts no ejecutan nuestro JS, así que sus escuchas no generan eventos detallados. Solo vemos las descargas del MP3, que registramos como evento `feed_download`.

## Revisión durante la implementación (2026-10-02)
- El feed y el audio responden también a **`HEAD`** (Apple y otras apps comprueban así el episodio antes de descargarlo) y a peticiones por rangos; verificado con `feedparser` y `curl -I` en producción.
- `feed_download` cuenta una descarga cuando la app pide el MP3 desde el byte 0 (no cada trozo, ni los `HEAD`).
- Sin capítulos JSON (`podcast:chapters`) por ahora: solo los muestran algunas apps.
- En Ajustes: copiar el enlace, botones de Apple Podcasts (Mac e iPhone) y Pocket Casts (móvil), y "Regenerar enlace" con confirmación. Overcast se descartó porque su enlace solo funciona en iPhone.
