# 04 · Resultados del spike de Google News (2026-10-01)

Script: [`backend/scripts/spike_google_news.py`](../../backend/scripts/spike_google_news.py). 6 búsquedas (3 en es-ES, 3 en en-US) × 10 ítems = 60 enlaces `news.google.com/rss/articles/…`.

## Tres formas de resolver el enlace a la URL del medio
| Vía | Cómo | Resultado |
|---|---|---|
| a) Redirecciones HTTP | `httpx.get(link, follow_redirects=True)` | **0/60.** Desde la UE, Google redirige a `consent.google.com` (muro de cookies). |
| b) `googlenewsdecoder` 0.2.1 | `gnewsdecoder(link)` | **0/60.** "Failed to fetch data attributes": también choca con el muro de consentimiento. |
| c) Lo que hace el navegador | cookie `SOCS` (consentimiento dado) → leer la firma `data-n-a-sg`/`data-n-a-ts` de la página del artículo → `POST /_/DotsSplashUi/data/batchexecute` → URL real | **60/60.** |

## Resumen
| Medida | Portátil (España) | VPS (Helsinki, producción) | Umbral |
|---|---|---|---|
| Enlaces resueltos (vía c) | 60/60 (100 %) | 60/60 (100 %) | ≥ 70 % |
| Texto extraíble ≥ 1.500 caracteres (trafilatura) | 41/60 (68 %) | 42/60 (70 %) | ≥ 50 % |
| Tiempo medio por enlace (vía c) | 0,22 s | 0,11 s | < 2 s |
| Respuestas 429 | 0 | 0 | ninguna |
| Texto por idioma | es 24/30, en 17/30 | es 25/30, en 17/30 | |

Los artículos sin texto suficiente son muros de pago, páginas con mucho JavaScript o piezas muy cortas (p. ej. Macleans.ca: 41 caracteres).

## Decisión
**Se mantiene Google News RSS** como fuente de descubrimiento, resolviendo los enlaces con la vía c (unas 20 líneas propias, sin dependencia: `googlenewsdecoder` no funciona desde la UE). Y, aunque es rápido, **solo se resuelven los enlaces de las historias elegidas por el editor** (paso 3): el editor trabaja con titular, medio y fecha, que el RSS ya trae.

**Riesgo aceptado:** `batchexecute` es un endpoint interno de Google y puede cambiar. Mitigación: Guardian y HN siguen dando candidatos con URL directa, el editor tiene historias de reserva y un test `@pytest.mark.live` detecta la rotura. Si se rompe, el plan B es GNews API (URLs directas).

## Salida completa (portátil)
```
## inteligencia artificial (es-ES): 10 items
  --B 0.37s   4106 chars  Mastermania
  --B 0.28s    341 chars  Media Stellantis
  --B 0.26s   7867 chars  Legálitas
  --B 0.29s   3709 chars  murciaplaza.com
  --B 0.26s     43 chars  Cinco Días
  --B 0.28s   3731 chars  Universidad Pontificia Comillas
  --B 0.26s   5207 chars  Ayuntamiento de Alhaurín el Grande
  --B 0.25s   2043 chars  Cadena SER
  --B 0.25s   2639 chars  Ayuntamiento de Elda
  --B 0.29s      0 chars  france24.com

## Real Madrid (es-ES): 10 items
  --B 0.24s    280 chars  realmadrid.com
  --B 0.21s   2723 chars  ABC
  --B 0.20s   4262 chars  Diario AS
  --B 0.21s   5272 chars  Cadena SER
  --B 0.21s   1821 chars  La Vanguardia
  --B 0.24s   3390 chars  El Periódico
  --B 0.23s   3378 chars  MARCA
  --B 0.21s   3975 chars  COPE
  --B 0.22s     43 chars  EL PAÍS
  --B 0.21s   2446 chars  RTVE.es

## vivienda (es-ES): 10 items
  --B 0.20s  10668 chars  La Moncloa. Gobierno de España
  --B 0.22s   6595 chars  El Mundo
  --B 0.23s   3611 chars  El Periódico
  --B 0.20s  10060 chars  Euskadi.eus
  --B 0.20s   3996 chars  La Voz de Galicia
  --B 0.22s   6282 chars  elDiario.es
  --B 0.21s   5795 chars  LaSexta
  --B 0.23s   5017 chars  Comunica GVA
  --B 0.20s   7303 chars  La Vanguardia
  --B 0.19s     43 chars  EL PAÍS

## AI regulation (en-US): 10 items
  --B 0.20s     43 chars  WSJ
  --B 0.19s  14341 chars  regulatoryoversight.com
  --B 0.19s     41 chars  Politico
  --B 0.17s   3414 chars  Insurance Journal
  --B 0.17s   2556 chars  ctnewsjunkie.com
  --B 0.18s    451 chars  Fox Business
  --B 0.18s    617 chars  ABC News - Breaking News, Latest News and Videos
  --B 0.22s     41 chars  axios.com
  --B 0.19s     43 chars  Reuters
  --B 0.17s   2202 chars  NBC News

## Formula 1 (en-US): 10 items
  --B 0.18s   4690 chars  Formula 1
  --B 0.20s   2222 chars  Yahoo Sports
  --B 0.19s   5793 chars  Motorsport.com
  --B 0.18s   7123 chars  Formula 1
  --B 0.20s   3400 chars  Yahoo Sports
  --B 0.21s   2127 chars  Formula 1
  --B 0.21s   3477 chars  Formula 1
  --B 0.17s   2763 chars  Formula 1
  --B 0.18s   3201 chars  Formula 1
  --B 0.19s    837 chars  Formula 1

## climate tech (en-US): 10 items
  --B 0.18s     43 chars  WSJ
  --B 0.20s    493 chars  WBUR
  --B 0.19s  14615 chars  Substack
  --B 0.17s     43 chars  Forbes
  --B 0.24s      0 chars  Bradenton Herald
  --B 0.30s   6354 chars  Light Reading
  --B 0.26s  35435 chars  Heatmap News
  --B 0.26s      0 chars  9News
  --B 0.33s     41 chars  Macleans.ca
  --B 0.26s   7494 chars  SBU News

## Summary
items: 60
a) resolved by plain redirects: 0/60
b) resolved by googlenewsdecoder: 0/60
c) resolved by batchexecute + SOCS cookie: 60/60
resolved (any): 60/60 = 100%
text >= 1500 chars: 41/60 = 68%
mean time: b) 0.12 s/item, c) 0.22 s/item
rate limited (429): 0
  es: resolved 30/30, text 24/30
  en: resolved 30/30, text 17/30
```
