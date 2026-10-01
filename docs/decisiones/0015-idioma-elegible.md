# 0015 · Idioma del podcast elegible por usuario

**Estado:** Aceptada

## Decisión
`preferences.language` (ISO 639-1). Afecta a:
1. la búsqueda de noticias (`hl`/`gl` en Google News; la Guardian y HN en inglés se traducen al resumir);
2. el idioma de salida del guionista;
3. las voces sugeridas.

La UI de la app estará en inglés y en español.

## Tradeoffs
- `eleven_v3` admite más de 70 idiomas con las mismas voces, así que no hace falta un catálogo de voces por idioma (aunque sugerimos voces nativas para ES y EN).
- Las noticias en un idioma minoritario pueden ser escasas: el editor puede mezclar fuentes en inglés y el guionista las narra en el idioma elegido.
