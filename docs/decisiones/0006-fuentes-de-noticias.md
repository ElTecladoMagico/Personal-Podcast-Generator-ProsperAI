# 0006 · Fuentes de noticias: RSS + APIs + scraping selectivo

**Estado:** Aceptada (spike de Google News superado el 2026-10-01)

## Contexto
El enunciado pide "pull news from APIs or scraping". Los intereses son texto libre, en cualquier idioma. Para un buen guion necesitamos el **texto completo** de las historias elegidas, no solo titulares.

## Decisión
Dos fases:
1. **Descubrimiento** (barato y amplio): por cada interés, unos 40 candidatos (título, medio, fecha, URL, extracto) de:
   - **Google News RSS** con búsqueda por tema e idioma (`hl`, `gl`): cubre cualquier tema y lengua.
   - **Exa** (búsqueda semántica, `POST /search`): entiende intereses en texto libre, cualquier idioma, y devuelve el **texto completo** de cada resultado. *(Sustituye a The Guardian el 2026-10-01; ver abajo.)*
   - **Hacker News (API de Algolia)**: tecnología en tiempo real.
2. **Profundización** (solo las 5–7 historias que elige el editor): descarga del artículo y extracción con **trafilatura**. Esto es el *scraping*.

Cada fuente es una función `fetch(interest, lang) -> list[Candidate]`. Sin clases ni registro de plugins.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **RSS + Exa + HN + scraping (elegida)** | Gratis (Exa: créditos gratuitos), en tiempo real, cualquier idioma, texto completo. Cumple "APIs y scraping". | Los enlaces de Google News vienen codificados (redirección): hay que resolverlos. Algunos medios bloquean el scraping o tienen muro de pago. |
| NewsAPI.org | API simple, 80k fuentes | Gratis **solo para desarrollo**, retraso de 24 h, contenido truncado. El siguiente plan cuesta 449 $/mes. |
| GNews | API simple, URLs directas | Gratis solo para uso no comercial, retraso de 12 h, sin texto completo |
| Webz.io / APITube / NewsAPI.ai | Texto completo, entidades, sentimiento | Cuotas gratuitas pequeñas. Otra cuenta. |
| OpenAI `web_search` | Encuentra cualquier cosa y devuelve citas | Caro por búsqueda, menos control y menos "nuestro". Respaldo útil para temas muy raros. |

## Riesgos y mitigación
- **Redirecciones de Google News**: spike de 1 h al inicio. Si no es fiable, sustituir por GNews (URLs directas) para el descubrimiento.
- **Scraping fallido o con muro de pago**: el editor recibe candidatos de reserva y, si falla la extracción, se usa el extracto del RSS o se elige la siguiente historia.
- **Términos del RSS de Google News**: el propio feed dice que es *"for personal, non-commercial use"* en un lector personal. Este proyecto (un reto técnico, sin ánimo de lucro, un podcast personal por usuario) encaja razonablemente; **un lanzamiento comercial exigiría sustituirlo** por una fuente con licencia (Exa ya lo es, o un agregador de pago). Anotado el 2026-10-01 al implementar la rama 5.
- **Licencias**: usamos el texto solo para generar un resumen propio, citamos el medio y enlazamos el original en las notas del episodio. Nunca republicamos el artículo.
- **Caché**: los artículos se cachean por URL para no repetir descargas entre usuarios con intereses parecidos.

## Resultado del spike (2026-10-01)
Detalle y salida completa en [`docs/plans/04-resultados.md`](../plans/04-resultados.md).
- Desde la UE (tanto en España como en el VPS de Helsinki), Google redirige los enlaces del RSS a su **muro de consentimiento de cookies**: ni las redirecciones HTTP ni el paquete `googlenewsdecoder` resuelven ninguno (0/60).
- Haciendo lo mismo que el navegador (cookie de consentimiento `SOCS` + firma de la página + `POST batchexecute`) se resuelven **60/60**, en 0,1–0,2 s y sin 429. El **70 %** tiene más de 1.500 caracteres de texto extraíble.
- **Decisión:** Google News se queda. Resolución propia (sin dependencia) y **solo para las historias elegidas** por el editor, en el paso 3.
- **Riesgo:** endpoint interno de Google, puede cambiar sin aviso → test `live`, y Exa/HN y las historias de reserva cubren la caída. Plan B: GNews API.

## Cambio: Exa sustituye a The Guardian (2026-10-01)
**Motivo:** la Open Platform de The Guardian exige un email de empresa para dar una key, y la key pública `test` ya devuelve **401**. Sin key no hay fuente.

| Opción | Pros | Contras |
|---|---|---|
| **API de Exa desde nuestro código (elegida)** | Búsqueda **semántica**: encaja con intereses en texto libre ("cómo afecta la IA a las panaderías"), donde las palabras clave del RSS fallan. Devuelve el texto completo (menos scraping), filtra por fecha de publicación, cualquier idioma. Una petición HTTP más, como HN. | Otra cuenta y otra key. De pago por uso: $20 de crédito inicial + $10/mes gratis; $0,007 por búsqueda con texto (~280 episodios/mes gratis con 5 intereses). |
| El LLM usando el MCP de Exa | Sin código de búsqueda | Un bucle de LLM decidiendo qué buscar: más tokens, más lento, menos predecible y más difícil de testear. Usa la misma API de Exa. |
| Solo Google News + HN | Ninguna cuenta | Peor con intereses de nicho; el texto depende 100 % del scraping (70 % de éxito, spike 04). |
| `web_search` de OpenAI | Sin cuenta nueva | Más caro por búsqueda, menos control de fuentes. |

**Petición** (siguiendo la skill oficial `build-with-exa`: no añadir parámetros sin una razón del producto): `query` = el interés en lenguaje natural ("latest news on …"), `type: "auto"`, `numResults` pequeño (decisión de producto), `startPublishedDate = since` (ventana obligatoria: lo publicado desde el último episodio) y `contents.text.maxCharacters = 6000` (el guionista necesita contexto amplio; el contrato recorta a 6.000). Sin `category` ni filtros de dominio (la skill los desaconseja). Si falta `EXA_API_KEY` o se agota el crédito, la fuente devuelve `[]` y el episodio sale con Google News + HN.

**Prueba (2026-10-01):** "latest news on Formula 1" y "últimas noticias sobre vivienda en España" → 4 resultados de las últimas 48 h cada una, 3 de 4 con más de 1.500 caracteres de texto, $0,007 por búsqueda.
