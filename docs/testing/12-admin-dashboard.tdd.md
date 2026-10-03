# TDD · `feat/admin-dashboard`

**Plan:** [`docs/plans/12-admin-dashboard.md`](../plans/12-admin-dashboard.md).

## Ciclos RED → GREEN
| Tarea | RED | GREEN |
|---|---|---|
| Métricas sobre un dataset escrito a mano | `ImportError: cannot import name 'metrics'` | 6 passed (152 en total) |
| DAU/MAU sobre 28 días | `0.214 == 0.0536` | 6 passed |
| Endpoint solo para admins | `404 == 403` | 2 passed (154) |
| Seed determinista | `ModuleNotFoundError: scripts.seed_mock_metrics` | 2 passed (156) |
| Conversión del embudo y formato | `Cannot find module './admin'` | 3 passed (35 en el frontend) |

## Qué garantizan los tests
| # | Garantía | Test |
|---|---|---|
| 1 | Altas y DAU por día, WAU de 7 días, embudo (4 → 3 → 2 → 1) | `test_metrics.py::test_growth…` |
| 2 | MAU, DAU/MAU (28 días), activación en 48 h, escucha completa media, 👍, coste por episodio con el precio de TTS | `…::test_kpis` |
| 3 | Retención: cohorte semanal y semana 0 relativa a cada alta | `…::test_retention…` |
| 4 | Histograma de escucha, saltos por posición, afinidad por tema (vía `work.selection`), adopción del RSS e importación | `…::test_content…` |
| 5 | p50 por etapa, fallos por etapa, episodios por día y disparador, verificador | `…::test_operations…` |
| 6 | Los simulados solo cuentan con `include_mock` | `…::test_mock_data_only_when_asked` |
| 7 | 403 sin rol `admin`; solo rangos 7/30/90 | `test_admin_api.py` |
| 8 | Misma semilla → mismos datos; solo filas `is_mock`, sin MP3; `reset` no toca usuarios reales; el seed llena todos los bloques | `test_seed_mock_metrics.py` |
| 9 | Conversión entre pasos y desde el inicio, sin dividir por cero; "—" cuando no hay datos | `src/lib/admin.test.ts` |

Interfaz verificada en el navegador (1440/390, claro/oscuro, Lighthouse): ver las notas del plan.
