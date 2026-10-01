# 0013 · Dashboard interno de métricas

**Estado:** Propuesta

## Contexto
El enunciado pide un dashboard interno de uso para entender el éxito del producto. Se permiten datos simulados.

## Decisión
Ruta `/admin` en la misma SPA, protegida por el rol admin de Clerk ([0005](0005-autenticacion.md)) y verificada también en el backend. Gráficos con **shadcn charts** (Recharts).

**Fuente única:** la tabla `events` (`user_id, type, episode_id, story_id, ts, props`). Los eventos los generan el reproductor y el backend. Un script con semilla (`seed_mock_metrics.py`) crea unos 200 usuarios ficticios y 90 días de histórico **con los mismos tipos de evento** que los reales, así que el dashboard no distingue unos de otros y los datos reales se suman encima.

Métricas:
- **Producto:** DAU/WAU/MAU, embudo (registro → onboarding → primer episodio → primera escucha completa → vuelve el día 7), retención por cohortes, % de escucha completa, saltos por capítulo, ratio 👍/👎, temas más populares.
- **Operación:** episodios por día, tasa de fallos por etapa, latencia por etapa (p50/p95), coste por episodio y por usuario (LLM + TTS).

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **Dashboard propio sobre `events` (elegida)** | Muestra que entendemos las métricas. Datos reales y simulados juntos. | Hay que escribir las consultas |
| PostHog / Mixpanel | Analítica completa gratis | El dashboard no es "nuestro". Configuración y otra dependencia. |
| Metabase o Grafana sobre Postgres | Potente | Un servicio más. No integrado en el producto. |
| Solo datos simulados en el frontend | Rapidísimo | No demuestra instrumentación real |

## Consecuencias
Las consultas viven en un único módulo `metrics.py` (SQL legible) para explicarlas fácilmente.
