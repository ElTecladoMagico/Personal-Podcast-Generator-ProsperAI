# 0012 · Onboarding: importar intereses desde tu IA

**Estado:** Aceptada

## Contexto
Rellenar intereses a mano es lento y pobre. ChatGPT y Claude ya **tienen memoria** del usuario. El onboarding es el primer "wow" del producto.

## Decisión
Tres caminos en la misma pantalla:
1. **Importar desde tu IA**: botón "Copiar prompt" → el usuario lo pega en su IA → pega aquí la respuesta.
2. **Chips sugeridos**: temas populares con un clic.
3. **Texto libre**.

El prompt pide un JSON cerrado:
```json
{"interests":[{"topic":"…","why":"…","weight":1-5}],
 "avoid":["…"],"sources_i_trust":["…"],
 "language":"es","tone":"casual|serious|nerdy","depth":"headlines|analysis"}
```
Se valida con Pydantic en el backend. Si la respuesta trae texto alrededor o bloques ```json, se extrae el primer objeto `{…}` válido. El resultado aparece como **chips animados editables** antes de guardar.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **Copiar/pegar prompt (elegida)** | Cero integraciones. Aprovecha la memoria que el usuario ya tiene en su IA. Muy original. | Requiere salir a otra pestaña. La salida de la IA puede venir mal formada (mitigado con extracción tolerante y error claro). |
| Onboarding conversacional con nuestro LLM | Inmersivo | Nuestro LLM no conoce al usuario: más pasos y más coste |
| Conectar Gmail, Calendar o historial (estilo Huxe) | Muy personalizado | OAuth sensible y revisión de permisos de Google. Excesivo para el alcance. |
| Solo formulario | Simple | Pobre y lento |

## Consecuencias
Mismo esquema JSON para importar y para guardar: el prompt documenta el modelo de preferencias.
