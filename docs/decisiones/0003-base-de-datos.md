# 0003 · Base de datos: PostgreSQL

**Estado:** Aceptada

## Contexto
Producto multiusuario: cuentas con preferencias, episodios, historias ya contadas (memoria) y eventos de uso (feedback y dashboard). Debe ser persistente y soportar acceso concurrente: API atendiendo usuarios mientras el pipeline escribe progreso.

## ¿Por qué no SQLite? (respuesta honesta)
SQLite **sí aguanta muchos usuarios**. Con modo WAL admite lecturas concurrentes ilimitadas y miles de escrituras por segundo, todas serializadas (un escritor a la vez). Para esta escala funcionaría. Sus límites reales son otros:
1. **Es un fichero ligado a una máquina**: imposible en Cloud Run o con varias instancias. Bloquea el camino de escalado de [0002](0002-despliegue.md).
2. **Un solo escritor**: el pipeline escribiendo progreso cada pocos segundos para varios usuarios a la vez compite con la API. Se gestiona, pero añade cuidados (`busy_timeout`, transacciones cortas).
3. **Analítica del dashboard**: Postgres tiene `date_trunc`, funciones de ventana y `JSONB` con índices, cómodos para las métricas.

## Decisión
**PostgreSQL 16** en un contenedor del mismo `docker compose`. Acceso con SQLAlchemy/SQLModel y migraciones con Alembic.

Modelo (5 tablas; `articles` se añadió en la planificación como la caché de extracción del ADR 0006):
- `users` (id de Clerk, preferencias en JSONB)
- `episodes` (estado, guion JSON con tiempos, ruta del audio, costes)
- `stories` (historias ya contadas, para memoria y seguimientos)
- `events` (reproducción, saltos, 👍/👎, fin de escucha)
- `articles` (caché de textos extraídos por URL, compartida entre usuarios, 48 h)

Esquema detallado: [`docs/plans/00-contratos.md` §4](../plans/00-contratos.md).

## Alternativas

| Opción | Gratis | Pros | Contras |
|---|---|---|---|
| **Postgres en la VPS (elegida)** | Sí | Cero cuentas externas, latencia mínima, idéntico en local y en producción | Backups a cargo nuestro |
| SQLite | Sí | Cero servidor, lo más simple | Ver arriba: no portable a Cloud Run y un solo escritor |
| Neon (Postgres serverless) | Capa gratuita (~0,5 GB, escala a cero) | Gestionado, backups y ramas de BD | Arranque en frío tras inactividad. Otra cuenta más. *Verificar límites actuales.* |
| Supabase | Capa gratuita (~500 MB) | Postgres + auth + storage en uno | **Pausa el proyecto tras ~7 días sin actividad**: mal para una demo que se evalúa días después |
| Firebase Firestore | Plan Spark: 1 GiB, 50k lecturas y 20k escrituras/día | Tienes cuenta. Tiempo real. SDK de Python. | NoSQL sin joins ni agregaciones flexibles: el dashboard (embudos, retención) se complica mucho. Cuotas diarias de lecturas que un dashboard agota rápido. Modelo de datos menos fácil de explicar. |
| Cloud SQL | No (~10 $/mes mínimo) | Gestionado por Google | De pago |

> Sobre los "5 GB gratis" de Firebase: corresponden a **Cloud Storage** (archivos), no a la BD. Desde el 3 de febrero de 2026 Cloud Storage for Firebase **exige el plan Blaze** (tarjeta), y los 5 GB gratuitos solo aplican a buckets en `us-central1`, `us-east1` o `us-west1`. Ver [0004](0004-almacenamiento-audio.md).

## Consecuencias
- Cambiar a Neon o Cloud SQL en el futuro = cambiar `DATABASE_URL`.
- El script `seed_mock_metrics.py` rellenará `events` con histórico simulado para el dashboard.

## Revisar si
Pasamos a Cloud Run: entonces Neon o Cloud SQL.
