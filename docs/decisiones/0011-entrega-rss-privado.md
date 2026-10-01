# 0011 · Entrega: feed RSS privado por usuario

**Estado:** Propuesta

## Contexto
"On a given schedule" se cumple de verdad si el episodio **llega solo** al usuario, sin tener que abrir nuestra web.

## Decisión
Cada usuario tiene `GET /feeds/<token>.xml`: un RSS de podcast estándar (etiquetas de iTunes, `enclosure` MP3 y notas con las fuentes). Se puede suscribir desde Apple Podcasts, Overcast o Pocket Casts. El token es aleatorio (32 bytes), se puede regenerar y revocar desde la UI, y también firma las URLs de audio de ese feed.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **RSS privado (elegida)** | Estándar abierto. Funciona en cualquier app de podcasts. Unas 40 líneas. | Quien tenga la URL puede escuchar (igual que los feeds privados de Patreon o Supercast). Mitigado con token revocable. |
| Push o email al estar listo | Aviso inmediato | Requiere un proveedor de email o push. No reproduce en la app de podcasts. |
| Solo reproductor web | Lo más simple | El usuario tiene que acordarse de entrar |

## Consecuencias
Las apps de podcasts no ejecutan nuestro JS, así que sus escuchas no generan eventos detallados. Solo vemos las descargas del MP3, que registramos como evento `feed_download`.
