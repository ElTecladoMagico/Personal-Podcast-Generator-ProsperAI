# 0006 · Fuentes de noticias: RSS + APIs + scraping selectivo

**Estado:** Aceptada (spike de Google News superado el 2026-10-01)

## Contexto
El enunciado pide "pull news from APIs or scraping". Los intereses son texto libre, en cualquier idioma. Para un buen guion necesitamos el **texto completo** de las historias elegidas, no solo titulares.

## Decisión
Dos fases:
1. **Descubrimiento** (barato y amplio): por cada interés, unos 40 candidatos (título, medio, fecha, URL, extracto) de:
   - **Google News RSS** con búsqueda por tema e idioma (`hl`, `gl`): cubre cualquier tema y lengua.
   - **The Guardian Open Platform**: gratis, uso comercial con atribución, **texto completo** vía `show-fields=body`.
   - **Hacker News (API de Algolia)**: tecnología en tiempo real.
2. **Profundización** (solo las 5–7 historias que elige el editor): descarga del artículo y extracción con **trafilatura**. Esto es el *scraping*.

Cada fuente es una función `fetch(interest, lang) -> list[Candidate]`. Sin clases ni registro de plugins.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **RSS + Guardian + HN + scraping (elegida)** | Gratis, en tiempo real, cualquier idioma, texto completo. Cumple "APIs y scraping". | Los enlaces de Google News vienen codificados (redirección): hay que resolverlos. Algunos medios bloquean el scraping o tienen muro de pago. |
| NewsAPI.org | API simple, 80k fuentes | Gratis **solo para desarrollo**, retraso de 24 h, contenido truncado. El siguiente plan cuesta 449 $/mes. |
| GNews | API simple, URLs directas | Gratis solo para uso no comercial, retraso de 12 h, sin texto completo |
| Webz.io / APITube / NewsAPI.ai | Texto completo, entidades, sentimiento | Cuotas gratuitas pequeñas. Otra cuenta. |
| OpenAI `web_search` | Encuentra cualquier cosa y devuelve citas | Caro por búsqueda, menos control y menos "nuestro". Respaldo útil para temas muy raros. |

## Riesgos y mitigación
- **Redirecciones de Google News**: spike de 1 h al inicio. Si no es fiable, sustituir por GNews (URLs directas) para el descubrimiento.
- **Scraping fallido o con muro de pago**: el editor recibe candidatos de reserva y, si falla la extracción, se usa el extracto del RSS o se elige la siguiente historia.
- **Licencias**: usamos el texto solo para generar un resumen propio, citamos el medio y enlazamos el original en las notas del episodio. Nunca republicamos el artículo.
- **Caché**: los artículos se cachean por URL para no repetir descargas entre usuarios con intereses parecidos.

## Resultado del spike (2026-10-01)
Detalle y salida completa en [`docs/plans/04-resultados.md`](../plans/04-resultados.md).
- Desde la UE (tanto en España como en el VPS de Helsinki), Google redirige los enlaces del RSS a su **muro de consentimiento de cookies**: ni las redirecciones HTTP ni el paquete `googlenewsdecoder` resuelven ninguno (0/60).
- Haciendo lo mismo que el navegador (cookie de consentimiento `SOCS` + firma de la página + `POST batchexecute`) se resuelven **60/60**, en 0,1–0,2 s y sin 429. El **70 %** tiene más de 1.500 caracteres de texto extraíble.
- **Decisión:** Google News se queda. Resolución propia (sin dependencia) y **solo para las historias elegidas** por el editor, en el paso 3.
- **Riesgo:** endpoint interno de Google, puede cambiar sin aviso → test `live`, y Guardian/HN y las historias de reserva cubren la caída. Plan B: GNews API.
