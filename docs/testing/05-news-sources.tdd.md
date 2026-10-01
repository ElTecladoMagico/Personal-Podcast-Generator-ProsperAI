# TDD · `feat/news-sources`

**Plan:** [`docs/plans/05-news-sources.md`](../plans/05-news-sources.md). Runner: `uv run pytest` (sin red); `uv run pytest -m live` (red real).

## Recorridos
- Como oyente, mis intereses (en cualquier idioma) producen una lista variada de noticias recientes de varias fuentes, sin repetidas ni temas que pedí evitar.
- Como oyente, aunque una fuente esté caída, mi episodio sale.
- Como sistema, nunca descargo dos veces el mismo artículo en 48 h, ni reintento una página bloqueada.

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| `normalize_url`, `normalize_title`, `dedupe` | `ModuleNotFoundError: app.sources` | 5 passed |
| Google News: URL del feed, parseo, firma y respuesta de `batchexecute` | `ImportError: google_news_feed_url` | 8 passed (+1 live) |
| Exa: parseo y sin key → sin llamada | `ImportError: parse_exa` | 10 passed (+1 live) |
| Hacker News: parseo, descarta Ask HN | `ImportError: parse_hn` | 11 passed |
| `gather_candidates`: ids, mezcla, fuente caída, `avoid`, dedupe y tope | `ImportError: gather_candidates` | 46 passed (total) |
| `extract_text` y `get_article` con caché | `ImportError: extract` | 6 passed (52 en total) |

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | URLs iguales salvo tracking, fragmento, barra final o mayúsculas del host cuentan como la misma | `test_sources.py::test_normalize_url…` |
| 2 | Se deduplica por URL o por título normalizado; gana el primero | `…::test_dedupe…` |
| 3 | El feed de Google News usa la edición del idioma (o la inglesa) y la ventana `when:Nd` | `…::test_google_news_feed_url…` |
| 4 | Del RSS: título sin " - Medio", medio, fecha en UTC, filtro por `since` | `…::test_parse_google_news…` |
| 5 | El resolvedor extrae la firma de la página y la URL de la respuesta de Google; ante un muro de consentimiento devuelve `None` | `…::test_resolver…` |
| 6 | Exa: dominio como medio, texto solo si ≥ 500 caracteres, fechas con zona; sin key no se llama | `…::test_parse_exa…`, `…::test_fetch_exa_without_key…` |
| 7 | HN: descarta posts sin URL | `…::test_parse_hn…` |
| 8 | `gather_candidates`: ids `c1..cN`, fuentes e intereses alternados, una fuente caída no rompe nada, `avoid` sin distinguir mayúsculas, dedupe entre fuentes, tope | `…::test_gather…`, `…::test_a_broken_source…`, `…::test_avoid…`, `…::test_dedupe_across…` |
| 9 | Extracción: cuerpo, título y og:image; una página sin artículo da `ok=False` | `test_extract.py::test_extract_text…` |
| 10 | Caché: una descarga por URL normalizada; refresco tras 48 h; los fallos recientes no se reintentan; los enlaces de Google News se resuelven antes y los irresolubles se descartan | `test_extract.py::test_get_article…`, `…::test_stale…`, `…::test_google_news_links…`, `…::test_download_failure…` |
| 11 | (live) Google News resuelve un enlace real; Exa devuelve artículos recientes con texto | `-m live` |

## Cobertura y huecos
`uv run --with pytest-cov pytest --cov=app` → 91 % total; `sources.py` 81 %, `extract.py` 73 %. Sin cubrir en los tests sin red: los envoltorios HTTP (`fetch_*`, `fetch_html`, `resolve_google_news`), que se ejercitan con los tests `live` y con `scripts/candidates_cli.py`.
