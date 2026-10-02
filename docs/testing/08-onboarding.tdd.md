# TDD · `feat/onboarding`

**Plan:** [`docs/plans/08-onboarding.md`](../plans/08-onboarding.md).

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| `compute_next_run` | `ModuleNotFoundError: app.schedule` | 8 passed |
| Guardar preferencias, importar, catálogo de voces | `ModuleNotFoundError: app.importer` | 14 passed (125 en total) |
| Lógica del asistente (añadir, fusionar lo importado, presentadores por defecto y por formato) | `Cannot find module './preferences'` | 4 passed (21 en el frontend) |

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | `off` nunca programa; diario/laborables/semanal en la zona del oyente, 20 min antes; si la antelación ya pasó, la siguiente ocurrencia; fin de semana saltado; cambio de hora (DST) sin mover la hora local; medianoche en otra zona | `test_schedule.py` |
| 2 | La primera vez que se guardan las preferencias: `onboarded`, `next_run_at` y `onboarding_completed {method}`; después, `preferences_updated`; `off` deja `next_run_at` en `null` | `test_preferences_api.py::test_first_save…` |
| 3 | Voces fuera del catálogo, sin intereses o zona horaria inexistente → 422 | `…::test_invalid_preferences_are_422` |
| 4 | El catálogo y la pareja por defecto por idioma (castellanas para `es`, inglesas para el resto) | `…::test_voices_catalog_and_defaults` |
| 5 | `extract_json` encuentra el JSON con texto alrededor, bloques ``` y llaves dentro de cadenas; falla claro sin JSON o con JSON inválido | `…::test_extract_json…` |
| 6 | La importación acota pesos, recorta a 12 intereses, normaliza el idioma y descarta tono o campos desconocidos | `…::test_import_is_tolerant…` |
| 7 | En el frontend: temas sin duplicados (sin distinguir mayúsculas) y máximo 12; lo importado se suma sin pisar lo ya elegido; presentadores nativos del idioma; 1 para `solo`, 2 para `duo`/`debate` | `src/lib/preferences.test.ts` |

E2E real en el navegador: ver las notas del plan.
