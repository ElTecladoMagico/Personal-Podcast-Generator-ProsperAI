# 0015 · Idioma del podcast elegible por usuario

**Estado:** Aceptada

## Decisión
`preferences.language` (ISO 639-1). Afecta a:
1. la búsqueda de noticias (`hl`/`gl` en Google News; Exa busca en cualquier idioma; HN, en inglés, se traduce al resumir);
2. el idioma de salida del guionista;
3. las voces sugeridas.

La UI de la app estará en inglés y en español.

## Tradeoffs
- `eleven_v3` admite más de 70 idiomas con las mismas voces, así que no hace falta un catálogo de voces por idioma (aunque sugerimos voces nativas para ES y EN).
- Las noticias en un idioma minoritario pueden ser escasas: el editor puede mezclar fuentes en inglés y el guionista las narra en el idioma elegido.

## Revisión durante la implementación (2026-10-02): solo español e inglés
Se ofrecían también francés, alemán, italiano y portugués, pero sin voces nativas (sonaban con acento inglés) ni un prompt probado en esos idiomas. Ahora `language` es `Literal["es", "en"]`: español de España (castellano) con voces de España afinadas en el [0008](0008-tts.md), o inglés. La importación desde la IA ignora otros idiomas y conserva el elegido; una migración de datos pasó los existentes a inglés. Añadir un idioma = voces nativas + revisar el prompt del guionista.
