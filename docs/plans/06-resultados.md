# 06 · Resultados de los episodios de prueba (2026-10-01)

Generados con `uv run python -m scripts.generate_episode_cli --minutes 2 …` (preferencias de `scripts/sample_prefs.json`: IA, vivienda en España, Fórmula 1, *climate tech*). Modelos: editor `gpt-6-luna`; guionista y verificador `gpt-6-sol`; voces ElevenLabs `eleven_v3` (Sarah + George).

| # | Idioma · formato | Estado | Tiempo total | Por etapa (s) | LLM (USD) | Tokens in/out | TTS (caracteres = créditos) | Duración MP3 | Verificador |
|---|---|---|---|---|---|---|---|---|---|
| 1 | es · duo | ready | 136 s | fetch 1,2 · edit 9,3 · research 0,4 · write 16,3 · verify 17,2 · record 91,2 | 0,052 | 18.957 / 3.692 | 2.322 | 163,0 s | 1 encontrado, 1 corregido |
| 2 | en · solo | ready | 96 s | fetch 1,3 · edit 10,8 · research 2,5 · write 13,7 · verify 2,3 · record 64,6 | 0,027 | 12.269 / 2.117 | 1.906 | 125,4 s | 0 |
| 3 | es · duo (matado en `recording`, reanudado) | ready | 70 s (solo `recording`) | write 14,9 · verify 2,4 · record 69,9 | 0,029 | 12.830 / 2.420 | 1.839 (+≈450 del tramo perdido) | 129,1 s | 0 |

## Lo aprendido
- **Ritmo de voz medido:** ~855 caracteres hablados por minuto (episodio 1: 2.322 caracteres → 163 s). Se fijó `CHARS_PER_MINUTE = 850`.
- **El guionista se pasaba un +25-30 %** del objetivo cuando era "±15 %". Ahora el objetivo es un **máximo** ("entre el 90 % y el 100 %") y se recorta a partir del +15 %: los episodios 2 y 3 duran 125 s y 129 s para 120 s.
- **Calidad del audio** (episodio 1): 0 errores de decodificación, duración de cabecera = duración real (162,97 s), ningún silencio > 1,5 s, sonoridad integrada −15,1 LUFS (estándar de podcast ≈ −16). ffmpeg avisa de *non monotonically increasing dts* al concatenar con `-c copy`: cosmético, el MP3 decodifica limpio.
- **Verificador:** con dos afirmaciones falsas plantadas a mano (una cifra inventada y una atribución a otro medio), detectó ambas (`unsupported`, `misattributed`), la reescritura las corrigió y no aparecen en el guion final. Coste: 0,03 USD.
- **Tiempos por palabra:** disponibles en todos los turnos de los tres episodios (el texto alineado por ElevenLabs coincide con el del guion).
- **Reanudación:** al matar el proceso durante `recording`, el episodio quedaba en `status=recording` sin `failed_stage` y el reintento empezaba desde cero. Corregido (`fix(pipeline): resume at the stage a crash interrupted`); el episodio 3 se reanudó solo en `recording`.
- **Coste de un episodio de 10 minutos (estimación):** ~0,08–0,12 USD de LLM, ~8.500 créditos de ElevenLabs, ~0,03 USD de Exa (4 búsquedas).
- **Tiempo:** la grabación domina (tramos secuenciales, uno por capítulo como mínimo). Para 10 minutos se esperan ~5–6 min en total: aceptable porque los episodios programados se generan 20 min antes (ADR 0010).
- **Continuidad entre tramos:** `eleven_v3` rechaza `previous_text` y `previous_request_ids` (400 *not supported by the 'eleven_v3' model*). Se mantiene la semilla fija por episodio y el corte en cambios de capítulo.

Pendiente de escucha humana (autor): naturalidad de las voces y de las transiciones entre tramos.
