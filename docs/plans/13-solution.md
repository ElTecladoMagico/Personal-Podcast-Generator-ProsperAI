# 13 · `docs/solution`

**Objetivo:** dejar la entrega impecable: `solution.md`, `sample.mp3`, README, diagrama final y una guía para que el autor **explique con seguridad** cada parte.
**Depende de:** todas.

## Entregables
1. **`sample.mp3`:**
   - el mejor episodio generado en producción: 10 min, formato dúo e idioma inglés (los evaluadores), con prompts ya afinados;
   - generar 2 candidatos con intereses variados y elegir el mejor escuchándolos enteros;
   - guardar también su guion en `docs/sample-transcript.md` (con las fuentes) para que se pueda verificar su fidelidad.
2. **`solution.md`** (en inglés, dirigido a los evaluadores):
   - **Overview:** qué es, enlace a la demo, cómo probarlo en 2 minutos (registrarse → importar desde su IA → generar → escuchar → preguntar → suscribirse por RSS).
   - **Feature tour:** capturas o GIF de: onboarding con importación, progreso en directo, reproductor, "Preguntar" y dashboard.
   - **Architecture:** diagrama (PNG exportado con archify + enlace al HTML interactivo); recorrido del pipeline de 6 pasos; modelo de datos; flujo de autenticación.
   - **Key decisions & trade-offs:** tabla resumen con enlaces a cada ADR (stack, VPS compartida frente a Cloud Run, Postgres frente a SQLite o Firestore, disco frente a R2, Clerk, fuentes y spike de Google News, editor LLM frente a embeddings, verificador, ElevenLabs, ffmpeg, polling frente a SSE, RSS, pool de hilos frente a cola externa).
   - **What's real vs mocked:** solo las métricas históricas del dashboard son simuladas; todo lo demás es real.
   - **Costs:** coste real por episodio (tokens, USD y créditos) de `06-resultados.md`, y estimación a 1.000 usuarios diarios.
   - **Scaling path:** qué cambiaría y en qué orden (Cloud Run + Postgres gestionado + R2 + Cloud Tasks; cola en Postgres con `SKIP LOCKED`; caché de artículos compartida; voces propias…).
   - **Limitations & next steps** (honesto).
   - **How I used AI tools:** Claude Code con skills (planificación por ADRs, ponytail, archify, revisión de código…) y en qué decisiones intervino el criterio humano.
   - **Metric definitions** (de la rama 12).
3. **`README.md`:** qué es (3 líneas), enlaces (demo, `solution.md`, docs), desarrollo local paso a paso y despliegue (enlace al runbook).
4. **Diagrama final:** regenerar `docs/arquitectura/architecture.json` con archify según lo construido de verdad (ver commits de las ramas) + exportar PNG.
5. **`docs/guia-explicacion.md`** (en español, para el autor):
   - una explicación de 1 párrafo por componente ("qué hace, por qué así, qué alternativa descartamos");
   - el recorrido de una petición de punta a punta;
   - **20 preguntas probables de los evaluadores con su respuesta** (p. ej. "¿por qué no una cola?", "¿qué pasa si ElevenLabs falla a mitad?", "¿cómo evitas alucinaciones?", "¿cómo escalarías a 100k usuarios?", "¿cómo sabes si el producto funciona?").

## Comprobaciones finales (checklist)
- [ ] Todos los ADRs reflejan lo construido (si algo cambió durante la implementación, actualizado con su motivo).
- [ ] `docs/plans/README.md` con todas las ramas en ✅.
- [ ] `/security-review` sobre el repo: sin secretos, auth en todos los endpoints privados, token del feed revocable, límites en `/ask` y `/events`.
- [ ] Producción: flujo completo con una cuenta nueva en Chrome de escritorio y Safari iOS.
- [ ] `seed_mock_metrics` aplicado en producción y el dashboard accesible con tu cuenta admin.
- [ ] Decisión sobre la instancia de Clerk de producción (ver plan 03), aplicada o documentada como pendiente.
- [ ] Créditos y coste total del proyecto anotados.

## Commits (en orden)
1. **`docs: sample episode and transcript`** (`sample.mp3`, `docs/sample-transcript.md`).
2. **`docs: final architecture diagram`**.
3. **`docs: solution overview`** (`solution.md`).
4. **`docs: README with local setup`**.
5. **`docs: explanation guide for the author`**.
6. **`docs: mark all plans done`**.

## Notas de implementación (2026-10-04)
- **`sample.mp3`:** 2 candidatos en inglés de 10 min (dúo, Sarah y George) con `scripts/sample_prefs_en.json`; elegido provisionalmente "Smarter AI, Moon Plans and a Rain-Soaked Grand Prix" (10:38, 5 historias, 0 avisos del verificador, 0,08 USD de LLM + 10.459 caracteres) leyendo los guiones; **pendiente de escucha del autor** (el otro: "AI Warnings, a Flying Ferry, and Singapore After Dark", 11:30). Guion con fuentes numeradas en `docs/sample-transcript.md`.
- **`sample-es.mp3`** (decisión del autor: inglés + castellano): los dos candidatos en castellano quedaron escritos y verificados, pero **la grabación falló por `quota_exceeded` de la key de ElevenLabs** (afecta también a producción). Se reanudan solo en `recording` con `generate_episode_cli --resume <id>` cuando haya cuota: `54639a6d-…` y `f07fea3a-…`.
- **ADRs al día** con lo construido: 0010 (hilo programador en vez de APScheduler), 0011 (`HEAD`, Pocket Casts, sin Overcast), 0014 (orbe CSS, barra fija en móvil, "Preguntar" y su latencia real), 0015 (solo `es`/`en`).
- **Diagrama** regenerado con archify (etiquetas reales: hilo cada 60 s, proxy *edge*, "ask", Pocket Casts) y exportado a PNG sin la barra de herramientas del visor. Un cruce menor de dos flechas junto al pipeline; una reubicación no lo mejoró y se mantuvo la disposición original.
- **Capturas** (UI en inglés, contenido en castellano) en `docs/img/` para el recorrido de `solution.md`.
- **Revisión de seguridad:** todos los endpoints privados piden JWT de Clerk, rol admin o el token de feed revocable; solo `/health` y `/voices` son públicos; sin claves en el repositorio (`git grep`) y los `.env` ignorados; límites activos en `/episodes` (5/día), `/ask` (10/hora) y `/events` (2 KB).
- **Arreglo encontrado al hacer las capturas:** las fechas de los episodios salían en el idioma del navegador, no en el de la app → `episodeDate(iso, lang)` con su test.
- **Pendiente del autor:** escuchar y confirmar los samples, subir la cuota de ElevenLabs, decidir sobre la instancia de producción de Clerk (documentado como limitación).
