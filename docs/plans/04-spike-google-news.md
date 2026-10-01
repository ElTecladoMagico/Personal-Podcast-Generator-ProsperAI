# 04 · `spike/google-news`

**Objetivo:** decidir con datos si Google News RSS sirve como fuente de descubrimiento (enlaces resolubles a la URL real del medio y texto extraíble). Duración máxima: **1 hora**.
**Depende de:** 1 (entorno `uv`). **ADR:** 0006.

## Contexto
Los `<link>` de Google News RSS son del tipo `https://news.google.com/rss/articles/CBMi…`: una redirección codificada que en un navegador resuelve JavaScript. Sin la URL real no se puede hacer scraping. Cada `<item>` sí trae el titular (`Titular - Medio`), `<source url="https://medio.com">Medio</source>` y `pubDate`.

## Experimento (script desechable `backend/scripts/spike_google_news.py`, se versiona como evidencia)
1. Feeds de búsqueda: `https://news.google.com/rss/search?q=<tema>+when:2d&hl=<hl>&gl=<GL>&ceid=<GL>:<lang>` para 3 temas × 2 idiomas: (`inteligencia artificial`, `Real Madrid`, `vivienda`) en es-ES y (`AI regulation`, `Formula 1`, `climate tech`) en en-US. 10 ítems por feed → **60 ítems**.
2. Resolver cada enlace por tres vías y medir aciertos y tiempo medio:
   a. `httpx.get(link, follow_redirects=True)` y mirar la URL final (esperado: falla o devuelve una página de consentimiento);
   b. paquete `googlenewsdecoder` (`gnewsdecoder(link, interval=1)`);
   c. si ambas fallan: `<source url>` + titular como "pista" (no sirve para el scraping, solo para el editor).
3. Para las URLs resueltas: `trafilatura` → ¿hay texto de más de 1.500 caracteres?
4. Imprimir una tabla resumen: % resueltas, % con texto, tiempo medio por ítem, errores 429.

## Regla de decisión

| Resultado | Decisión |
|---|---|
| ≥ 70 % resueltas **y** ≥ 50 % con texto **y** < 2 s/ítem, sin bloqueos | **Mantener Google News** (vía b) |
| Resolución fiable pero lenta o con 429 | Mantener, pero **resolver solo las historias elegidas por el editor** (paso 3), no los 60 candidatos |
| No fiable | Sustituir por **GNews API** (`gnews.io`, URLs directas, gratis 100 peticiones/día para uso no comercial; suficiente para el reto) y pedir la key al autor |

## Entregables (commits)
1. **`chore(spike): google news resolution experiment`**: el script + la salida pegada en `docs/plans/04-resultados.md`.
2. **`docs: record google news decision in ADR 0006 and plan 05`**: actualizar el ADR 0006 (sección "Resultado del spike") y el plan 05 si cambia la fuente.

**Merge:** sí (el resultado documentado forma parte del razonamiento de `solution.md`).
