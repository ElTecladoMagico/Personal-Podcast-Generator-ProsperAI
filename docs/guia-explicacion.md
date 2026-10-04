# Guía para explicar el proyecto

Para el autor: cómo contar cada parte con seguridad, por qué está hecha así y qué alternativa se
descartó. Los detalles están en los ADR ([`decisiones/`](decisiones/README.md)) y en
[`solution.md`](../solution.md).

## La idea en 30 segundos
Una "redacción" automática por oyente. Cada día, a su hora, seis pasos encadenados buscan noticias de
sus temas, eligen las que merecen la pena, leen los artículos, escriben una conversación entre dos
presentadores en la que cada dato apunta a su artículo, la verifican contra las fuentes y la graban con
ElevenLabs. El episodio llega al reproductor web y a su app de podcasts por un RSS privado. Un dashboard
interno responde "¿funciona el producto?".

Tres principios: **la lógica más simple que funcione, una UX que impresione y un producto multiusuario
de verdad.**

## Cada componente en un párrafo

- **Frontend (React + Vite + shadcn, en Netlify).** Una SPA estática: gratis de alojar y rápida. TanStack
  Query gestiona los datos y el *polling*; la interfaz está en español e inglés. El dashboard y Recharts
  se cargan solo en `/admin`. *Descartado:* Next.js; no necesitamos servidor en el frontend.
- **Backend (FastAPI, un proceso, en un VPS con Docker Compose).** Código síncrono, más fácil de leer y
  depurar que `async`. Sirve la API, los feeds RSS y los MP3. *Descartado:* Cloud Run; ffmpeg, un disco
  y trabajos de minutos encajan mejor en un VPS que ya teníamos, y migrar está documentado.
- **Postgres.** Varios escritores a la vez, JSONB para el estado del pipeline y, sobre todo, un **índice
  único parcial** que garantiza un solo episodio en producción por usuario sin código de bloqueo.
  *Descartado:* SQLite (un escritor y no portable a Cloud Run) y Firestore.
- **Clerk.** Registro, Google, sesiones y el rol de admin sin escribir autenticación. La API verifica el
  JWT con las claves públicas de Clerk. El audio y el RSS no pueden mandar un JWT, así que usan un
  **token de feed** aleatorio y revocable.
- **Fuentes.** Google News RSS (cualquier tema e idioma; resolvemos sus enlaces al artículo real),
  **Exa** (búsqueda semántica que devuelve el texto completo) y Hacker News. Lectura con trafilatura y
  caché de 48 h. *Descartado:* The Guardian (pide email de empresa) y NewsAPI (de pago para producción).
- **Pipeline de 6 pasos** (`backend/app/pipeline/`). Cada paso es una función que recibe y devuelve un
  objeto `Work` tipado que se guarda tras cada paso: si algo falla o el servidor se reinicia, se reanuda
  en ese paso sin repetir lo hecho ni volver a pagarlo. *Descartado:* un único prompt gigante
  (inexplicable, imposible de verificar y de reanudar).
- **Modelos.** `gpt-6-luna` (barato) para elegir historias y responder preguntas; `gpt-6-sol` para escribir
  y verificar, porque es lo que se oye. Salidas estructuradas (Pydantic) en todos los pasos.
- **Verificador.** Comprueba cada frase con datos contra sus artículos (sin respaldo, exagerada, mal
  atribuida, desactualizada); el guionista la reescribe una vez y lo que siga marcado se elimina. Es la
  promesa del producto: confianza.
- **Voces (ElevenLabs Text to Dialogue, `eleven_v3`).** Una conversación de dos voces en una sola petición,
  con marcas de tiempo por palabra (la transcripción sincronizada). Se graba en trozos en paralelo, se
  une con ffmpeg y se acelera ×1,1. Para español, voces de España elegidas en una prueba A/B.
- **Programación sin cola.** Un hilo que cada 60 s lanza los episodios cuya hora ha llegado (20 min antes
  de la hora del oyente, respetando el cambio de hora) y borra el audio de más de 30 días. Un *pool* de 3
  hilos produce los episodios. *Descartado:* Celery + Redis o Cloud Tasks; demasiada infraestructura
  para esta escala.
- **RSS privado.** Un feed estándar por usuario (etiquetas de iTunes, `HEAD` y rangos como exige Apple):
  el episodio llega solo a la app de podcasts que ya usa.
- **"Pregunta a los presentadores".** Pausa, pregunta sobre la historia en curso; el modelo responde
  como los presentadores **solo con los artículos de esa historia** (y lo dice si no lo cuentan), se graba
  con las mismas voces y el episodio sigue 2 s antes.
- **Dashboard.** Todo sale de una tabla `events` y de `episodes`, con SQL calculado al vuelo (~130 ms
  con 90 días). Los mismos eventos alimentan al editor (👍/👎 y saltos) y al dashboard. Los datos
  simulados están marcados (`is_mock`) y se pueden ocultar.

## Una petición de punta a punta: "Generar ahora"
1. El navegador hace `POST /episodes` con el JWT de Clerk. La API comprueba que el usuario ha hecho el
   onboarding y el límite diario; crea el episodio `queued` (si ya hay uno en curso, el índice único lo
   impide → 409) y lo manda al *pool*.
2. Un hilo ejecuta los pasos: **reporter** (hasta 60 candidatas en paralelo) → **editor** (elige según
   intereses, pesos, lo ya escuchado y el feedback) → **research** (texto completo, 2 medios por historia)
   → **writer** (capítulos y turnos con `source_ids`) → **checker** → **voice** (MP3 + tiempos por palabra).
   Cada paso guarda su resultado, su coste y su duración.
3. Mientras tanto, la página pregunta cada 1,5 s `GET /episodes/{id}` y pinta los números reales de cada
   etapa ("59 noticias de 39 medios…").
4. Al terminar: `status = ready`, se guarda la memoria de historias (para no repetir mañana) y un evento
   `episode_ready` con coste y tiempos. El reproductor carga el MP3 con el token del feed.

## 20 preguntas probables (con respuesta)

1. **¿Por qué no una cola (Celery, Redis, SQS)?** Con un proceso, un *pool* de hilos *es* la cola y el
   límite de concurrencia. La base de datos garantiza un episodio por usuario. Si hubiera dos instancias,
   el siguiente paso es Postgres como cola (`FOR UPDATE SKIP LOCKED`), no Redis.
2. **¿Qué pasa si ElevenLabs falla a mitad?** El paso de voz falla, el episodio queda `failed` en
   `recording` con el error, y "Reintentar" reanuda **solo** la grabación: el guion y la verificación ya
   están guardados. Si el servidor se reinicia, al arrancar se reanudan solos. (Pasó de verdad: la cuota
   de la key se agotó y los episodios quedaron pendientes de grabar, sin perder nada.)
3. **¿Cómo evitas las alucinaciones?** Tres capas: el guionista solo recibe los artículos y debe citar
   el `id` de cada dato; un verificador independiente compara cada frase con sus fuentes; lo que no se
   corrige, se elimina. Y en "Preguntar", si las fuentes no lo cuentan, los presentadores lo dicen.
4. **¿Cómo sabes si el producto funciona?** Activación (escuchar ≥ 80 % del primer episodio en 48 h),
   retención semanal por cohortes, DAU/MAU, escucha completa y saltos, y coste por episodio. Cada métrica
   tiene su definición exacta en el dashboard.
5. **¿Cómo escalarías a 100.000 usuarios?** Primero el coste (abajo). Después: varias instancias con
   Postgres como cola, audio en R2, Cloud Run y Postgres gestionado. Y compartir lo caro: buscar y leer las
   noticias de un tema es igual para todos los que lo siguen; solo editor, guion y voces son personales.
6. **¿Cuánto cuesta un episodio?** ~2,4 USD los 10 minutos: 0,08 de LLM y ~2,3 de voz. La voz es el
   ~95 %. Palancas: 5 minutos por defecto, precio por volumen, y no generar para quien no escucha.
7. **¿Por qué Google News si sus términos no lo permiten?** Fue la mejor cobertura en el *spike*, para
   cualquier tema e idioma. Es un riesgo conocido y documentado: si se rompe, Exa y HN siguen funcionando,
   y en producción iría una API de noticias de pago.
8. **¿Por qué un VPS y no la nube?** ffmpeg, un disco y trabajos de minutos encajan bien en un VPS que ya
   existía, a coste cero. El frontend está en Netlify y la migración a Cloud Run está escrita.
9. **¿Por qué polling y no WebSockets o SSE?** `EventSource` no puede mandar la cabecera con el JWT. Con
   TanStack Query el polling es una línea, y ~100 peticiones mínimas por episodio no importan.
10. **¿Cómo personalizas?** Pesos por interés, temas a evitar, medios de confianza, la memoria de lo que
    ya escuchó (seguimientos en vez de repeticiones), y su feedback: 👍/👎 y saltos de los últimos 30 días
    los recibe el editor del siguiente episodio.
11. **¿Cómo consigues la transcripción sincronizada?** ElevenLabs devuelve el alineamiento por carácter;
    lo convertimos en tiempos por palabra y, tras acelerar ×1,1, se dividen los tiempos por 1,1.
12. **¿Qué es "Importar desde tu IA"?** Copias un prompt en ChatGPT o Claude, que ya te conocen, y pegas
    su respuesta: extraemos el JSON aunque venga con texto alrededor y acotamos los valores raros. Sin
    integraciones ni OAuth.
13. **¿Cómo se programa a la hora correcta en cada zona horaria?** Se calcula en la zona del oyente (con
    el cambio de hora), 20 minutos antes, y se guarda en UTC; el hilo mira cada minuto quién toca.
14. **¿Es seguro el RSS privado?** Quien tenga la URL puede escuchar (como los feeds privados de Patreon);
    por eso el token es aleatorio, de 32 bytes, y se puede regenerar al momento desde Ajustes.
15. **¿Qué es real y qué es simulado?** Todo es real salvo el histórico del dashboard: 200 oyentes
    simulados con semilla fija, marcados y ocultables.
16. **¿Qué harías con más tiempo?** Reproducir la respuesta de "Preguntar" mientras se genera (bajar de
    ~10 s), no generar para quien no escucha, Clerk de producción y una API de noticias de pago.
17. **¿Cómo has probado esto?** TDD en cada rama (163 tests de backend con Postgres real y 39 de
    frontend), ejecuciones reales de cada paso con sus costes, y E2E en producción con una cuenta nueva:
    hasta un episodio programado que llegó solo al feed.
18. **¿Qué parte te costó más?** La naturalidad del audio (voces de España, estabilidad *creative*,
    ×1,1) y que el guion cumpla la duración (el modelo se pasaba un 25–30 %; ahora es un máximo con recorte).
19. **¿Qué decisiones tomaste tú y cuáles la IA?** Yo decidí las de producto y arquitectura (Exa cuando
    falló The Guardian, un proxy neutral para no depender de otro proyecto del servidor, las voces tras la
    prueba A/B, recortar lo que no cumplía su promesa). Claude Code implementó sobre planes y ADR escritos
    antes, con tests primero y revisiones.
20. **Si tuvieras que quitar una pieza, ¿cuál?** El scraping de Google News, por su riesgo legal: Exa ya
    da texto completo. Y lo que **no** quitaría es el verificador: es lo que hace creíble el producto.

## Cifras para tener a mano
- Episodio de 10 min: ~2,5 min de producción; 0,08 USD de LLM + ~10.500 caracteres de voz.
- "Preguntar": 8,5–12,7 s y ~0,07 USD por respuesta; límite de 10 por episodio y hora.
- Dashboard: ~130 ms con 90 días de datos simulados.
- Límites: 5 episodios manuales al día por usuario; 1 en producción a la vez.
