# 12 · `feat/admin-dashboard`

**Objetivo:** un dashboard interno que responda **"¿está funcionando el producto?"**: crecimiento, activación, hábito, calidad del contenido y salud y coste de la operación. Datos simulados con semilla + datos reales, de la misma tabla `events`.
**Depende de:** 9, 10. **Prerrequisito:** tu usuario con `public_metadata.role = "admin"` en Clerk. **ADR:** 0013.

## Definiciones (deben figurar también en la UI, en un "ℹ︎" junto a cada métrica)

| Métrica | Definición exacta |
|---|---|
| **Usuario activo (día)** | Usuario con ≥ 1 evento de escucha (`play_started`, `listen_progress`, `feedback`, `chapter_*`, `ask_asked`) o `feed_download` ese día (UTC) |
| DAU / WAU / MAU | Usuarios activos distintos en 1 / 7 / 28 días hasta la fecha |
| *Stickiness* | DAU medio / MAU |
| **Activación** | % de registrados en el rango que completan su primera escucha ≥ 80 % en sus primeras 48 h |
| Embudo | Cohorte registrada en el rango: `user_signed_up` → `onboarding_completed` → primer `episode_ready` → primera escucha ≥ 80 % → vuelve a escuchar entre el día 7 y el 13 |
| Retención semanal | Cohortes por semana de registro × semana N (0–8): % con ≥ 1 día activo en esa semana |
| **Escucha completa** | Por (usuario, episodio): `max(max_position_s) / duration_s`; se muestra la media y un histograma por deciles |
| Tasa de saltos por posición | `chapter_skipped` / `chapter_started` agrupado por índice de capítulo (1ª historia, 2ª…) |
| Afinidad por tema | Por interés: escuchas de capítulos, ratio 👍/(👍+👎) y tasa de saltos (mapeando `story_id → interest` con `episodes.work.selection`) |
| Adopción del RSS | % de usuarios activos con ≥ 1 `feed_download` en el rango |
| Onboarding por importación | % de `onboarding_completed` con `method = import` |
| Uso de "Preguntar" | Preguntas por día, % de usuarios activos que preguntan y latencia p50/p95 |
| **Latencia por etapa** | p50/p95 de `episodes.stage_timings[stage]` (episodios `ready` del rango) |
| Fallos por etapa | Recuento de `episode_failed` por `props.stage` y % sobre los solicitados |
| **Coste por episodio** | Media de `cost.llm_usd` + `cost.tts_chars × precio por crédito` (constante `TTS_USD_PER_CHAR`, anotada desde el plan de ElevenLabs) y su serie temporal |
| Calidad factual | % de turnos corregidos o eliminados por el verificador (`issues_fixed + turns_removed` / turnos) |

## Backend
- **`app/metrics.py`:** una función por bloque, cada una **una consulta SQL legible** (CTEs con nombre; nada de ORM complejo), parametrizada por `start`, `end` e `include_mock`:
  - `kpis()`, `active_users_series()`, `funnel()`, `retention_cohorts()`, `listening()`, `topics()`, `operations()`, `costs()`, `features()`.
- **`GET /admin/metrics?range=7d|30d|90d&include_mock=true`** (`require_admin`) → JSON con todos los bloques. Se calcula al vuelo; con unos 200 usuarios simulados × 90 días (~150k eventos) cada consulta tarda < 100 ms con los índices de §4. *ponytail:* sin caché ni vistas materializadas mientras sea así.
- **`scripts/seed_mock_metrics.py --users 200 --days 90 --seed 42 [--reset]`**:
  - **Usuarios:** altas con curva de crecimiento (más en las últimas semanas), `is_mock = true`, `clerk_id = "mock_<n>"`, `feed_token` aleatorio (nunca se programan; ver rama 10).
  - **Onboarding:** 80 % lo completa, el 45 % por importación; intereses de un catálogo de ~30 temas; frecuencias 60 % diaria, 25 % laborables, 10 % semanal, 5 % a demanda.
  - **Episodios:** según la frecuencia, con 3 % de fallos repartidos por etapa (más en `recording` y `fetching`); `stage_timings` con distribución log-normal por etapa; `cost` realista (tomado de `06-resultados.md`); `audio_expired = true` y sin MP3. `work.selection` mínimo (interés por historia) para la afinidad.
  - **Comportamiento:** compromiso por usuario con decaimiento (retención realista: ~45 % en la semana 1 y ~25 % en la 8); completitud con distribución beta; saltos más probables en los intereses de poco peso y en las últimas historias; feedback en el 15 % de los capítulos (👍 70 %); `feed_download` en el 35 % de los usuarios; "Preguntar" en el 12 %.
  - **Idempotente:** `--reset` borra todo lo `is_mock` (borrado en cascada por `user_id`) y regenera.
- **Tests (`tests/test_metrics.py`):** un dataset pequeño y determinista insertado en el *fixture* (5 usuarios, 10 episodios y eventos escritos a mano) → valores exactos de DAU, embudo, completitud, tasa de saltos y p50 de etapas.

## Frontend `/admin`
- Acceso: si `!me.is_admin` → 404 (no se revela que existe).
- **Cabecera:** selector de rango (7/30/90 días), interruptor "Incluir datos simulados" (por defecto sí, con la insignia "Mocked + real") y hora de actualización.
- **Fila de KPIs** (tarjetas con el valor, el delta frente al periodo anterior y una mini serie): MAU, DAU/MAU, activación, escucha completa media, ratio 👍 y coste por episodio.
- **Pestañas:**
  1. **Crecimiento y hábito:** DAU/WAU/MAU (líneas), altas por día (barras), embudo (barras horizontales con el % de conversión entre pasos) y retención por cohortes (tabla mapa de calor).
  2. **Contenido:** histograma de escucha completa, saltos por posición, afinidad por tema (barras ordenadas por 👍; color = tasa de saltos), uso de "Preguntar" y adopción del RSS.
  3. **Operación:** episodios por día (apilado manual/programado), latencia p50/p95 por etapa, fallos por etapa, coste por episodio (LLM frente a TTS, área apilada) y calidad factual.
- Cada gráfico lleva una frase de "**por qué importa**" (p. ej. "La activación en 48 h es el mejor predictor de retención: si no escuchan el primer episodio, no vuelven"). Demuestra criterio de producto, que es parte de la evaluación.
- Gráficos con shadcn charts (Recharts). **Antes de escribir los gráficos, cargar la skill `dataviz`** (paleta, accesibilidad, modo claro y oscuro).

## Commits (en orden)
1. **`feat(metrics): metric definitions and SQL queries`** + tests con el dataset determinista.
2. **`feat(api): admin metrics endpoint`** + test de 403/404 para no admins.
3. **`chore(scripts): deterministic mock metrics seed`**.
4. **`feat(frontend): admin layout, range and mock toggle, KPI row`**.
5. **`feat(frontend): growth and habit charts`**.
6. **`feat(frontend): content charts`**.
7. **`feat(frontend): operations charts`**.
8. **`docs: metric definitions`** (copiar la tabla de definiciones a `solution.md` en la rama 13).

## Verificación final
- `seed_mock_metrics.py --reset` en local y en producción → el dashboard muestra tendencias creíbles.
- Con el interruptor de datos simulados apagado, solo se ven tus datos reales (coherentes con lo que hiciste en la app).
- Revisar que cada número de una tarjeta coincide con una consulta manual (3 comprobaciones).
- `improve` + revisión de accesibilidad de los gráficos (contraste y etiquetas).

## Criterios de aceptación
- [ ] Todas las métricas de la tabla visibles, con su definición.
- [ ] Responde en < 1 s con el seed completo.
- [ ] Solo accesible para admins (verificado en el backend).
