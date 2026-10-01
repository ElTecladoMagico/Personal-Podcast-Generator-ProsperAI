# 05 · `feat/news-sources`

**Objetivo:** dadas unas `Preferences`, obtener unos 40–60 `Candidate` frescos y diversos (paso 1), y extraer el texto completo de cualquier URL con caché (lo usa el paso 3).
**Depende de:** 4 (decisión sobre Google News). **Prerrequisito:** `GUARDIAN_API_KEY` (vale `test` con límites). **ADR:** 0006.

## Diseño
`app/sources.py`: tres funciones puras de red, sin clases.
```python
def fetch_google_news(interest: str, lang: str, since: datetime, limit=8) -> list[Candidate]
def fetch_guardian(interest: str, since: datetime, limit=4) -> list[Candidate]   # trae text (bodyText)
def fetch_hn(interest: str, since: datetime, limit=5) -> list[Candidate]          # points > 20
def gather_candidates(prefs: Preferences, since: datetime) -> list[Candidate]
```
- `gather_candidates`: para cada interés × fuente, en paralelo con `ThreadPoolExecutor(8)`; normaliza, deduplica, recorta y asigna ids `c1..cN`.
  - **Normalización de URL:** minúsculas en el host, sin `utm_*`, `fbclid`, `#…` ni barra final.
  - **Deduplicación:** misma URL normalizada, o título normalizado (minúsculas, sin puntuación) idéntico.
  - **Exclusión:** si `avoid` aparece en el título o el extracto (*case-insensitive*), fuera.
  - **Tope:** 60 candidatos, repartidos de forma equilibrada por interés y priorizando los de más peso.
- **Google News:** `feedparser.parse(url)`. URL de búsqueda con `hl`/`gl`/`ceid` derivados de `lang` (tabla pequeña: es→ES, en→US, fr→FR, de→DE, it→IT, pt→BR; otros → en-US). Título sin el sufijo ` - Medio`; `url` = el enlace `news.google.com/rss/articles/…` tal cual (el editor no necesita la URL real). **Resolución (spike 04, [resultados](04-resultados.md)):** `resolve_google_news(link, client) -> str | None` en `sources.py`, con la vía c del spike (cookie `SOCS` + firma de la página + `POST batchexecute`). La llama `get_article` **solo** cuando el host es `news.google.com`, es decir, solo para las historias elegidas. Sin `googlenewsdecoder` (no funciona desde la UE).
- **Guardian:** `GET https://content.guardianapis.com/search` con `q`, `from-date`, `order-by=relevance`, `show-fields=bodyText,trailText,thumbnail`, `page-size`, `api-key`. `text = bodyText[:6000]`.
- **HN (Algolia):** `GET https://hn.algolia.com/api/v1/search?query=…&tags=story&numericFilters=created_at_i>{ts},points>20&hitsPerPage=…`. Se ignoran los ítems sin `url` (Ask HN).
- `since` = fecha del último episodio `ready` del usuario, o hace 48 h (diario) / 8 días (semanal). Mínimo 24 h.
- HTTP: un `httpx.Client(timeout=10, headers={"User-Agent": "PersonalPodcastBot/1.0 (+https://podcast.scuda.es)"})` compartido. Si una fuente falla, se registra y se devuelve `[]`: **una fuente caída nunca tumba el episodio**.

`app/extract.py`:
```python
def get_article(url: str, session) -> ArticleText | None   # usa la tabla articles (caché 48 h)
```
- Si está en caché y es reciente → se devuelve. Si no: GET con `follow_redirects`, límite de 2 MB y solo `text/html`; `trafilatura.extract(html, favor_precision=True)` y `trafilatura.extract_metadata(html)` (título, `image`). Se guarda en `articles` (`ok=False` si no hay texto, para no reintentar durante 48 h).
- Muros de pago o bloqueos: no se intenta esquivarlos; `ok=False`.

## Commits (en orden)
1. **`feat(sources): candidate model helpers (normalize, dedupe)`**: `normalize_url`, `normalize_title`, `dedupe` + tests.
2. **`feat(sources): Google News RSS fetcher and link resolver`**: + test con un RSS de *fixture* grabado (`tests/fixtures/google_news_es.xml`); test puro del parseo de la respuesta de `batchexecute` (*fixture*) y un test `@pytest.mark.live` que resuelve un enlace real (detecta si Google cambia el endpoint).
3. **`feat(sources): Guardian fetcher`**: + test con un JSON de *fixture*.
4. **`feat(sources): Hacker News fetcher`**: + test con un JSON de *fixture*.
5. **`feat(sources): gather_candidates with parallel fetch, avoid filter and cap`**: + test con las fuentes parcheadas (funciones puras inyectadas como argumento por defecto, para no mockear la red).
6. **`feat(extract): article extraction with cache table`**: + test de `extract_text(html)` con 2 HTML de *fixture* (uno con contenido y uno sin él).
7. **`chore(scripts): candidates CLI`**: `scripts/candidates_cli.py --prefs scripts/sample_prefs.json` imprime una tabla de candidatos (útil para afinar y para la demo). Añade `scripts/sample_prefs.json` (intereses en ES y EN).

## Verificación final
- `uv run pytest` en verde, sin red.
- `uv run python scripts/candidates_cli.py` (red real, `@live`): ≥ 30 candidatos para `sample_prefs.json`, de al menos 2 fuentes, sin duplicados evidentes, en < 10 s.

## Criterios de aceptación
- [ ] Cada fuente funciona de forma aislada y su fallo no rompe las demás.
- [ ] Los candidatos respetan `since` y `avoid`.
- [ ] La caché evita descargar dos veces la misma URL en 48 h.

## Riesgos
- Cuota de la key `test` de Guardian (muy baja) → pedir la key real pronto.
- El RSS de Google News tiene ~100 ítems como máximo y a veces devuelve resultados antiguos → `when:2d` en la query y filtro por `pubDate`.
