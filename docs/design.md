# Diseño · "estudio de radio nocturno"

**Propósito:** escuchar tu podcast diario y ajustar lo que quieres oír. **Público:** una persona que vuelve cada mañana: lo primero que busca es el episodio de hoy y el botón de play.
**Tono:** editorial y tranquilo, de noche. **Detalle memorable:** el piloto **ON AIR**, un único acento cálido que se enciende cuando algo "está en antena" (generando, reproduciendo, botón principal).

## Paleta (tokens en `frontend/src/index.css`, formato shadcn, OKLCH)
| Token | Oscuro (por defecto) | Claro | Uso |
|---|---|---|---|
| `background` | pizarra azulada muy oscura `0.16 0.012 255` | papel cálido `0.985 0.004 80` | fondo |
| `foreground` | blanco cálido | tinta pizarra | texto |
| `primary` | rojo anaranjado ON AIR `0.68 0.19 35` | `0.55 0.2 32` | CTA, reproducción, "en antena" |
| `signal` | ámbar `0.8 0.13 75` | `0.52 0.12 65` | estados secundarios (en cola, avisos) |
| `muted-foreground` | pizarra clara | pizarra media | texto secundario |
| `chart-1..5` | rojo, ámbar, verde azulado, azul, malva | ídem | gráficos del dashboard (tonos distintos, no un solo color) |

Neutros **fríos** + acento **cálido**: evita la paleta de un solo tono y el típico degradado morado. Contraste comprobado (WCAG AA ≥ 4,5:1) para texto principal, secundario, `primary`, `signal` y `destructive` sobre el fondo en ambos temas; mínimo medido 5,1:1.

## Tipografía
- **Titulares (`h1`, `h2`, `font-heading`):** *Instrument Serif* (regular e itálica). Expresiva, de revista; la itálica para el énfasis ("*made for you*").
- **Interfaz (`font-sans`):** *Geist Variable*. Neutra y legible en tamaños pequeños.
- Ambas autoalojadas con fontsource (sin peticiones a Google Fonts).

## Espaciado y forma
- Radio base `0.75rem` (escala de shadcn). Mucho aire: secciones con `py-16`/`py-24` en la landing, `gap-6` en la app.
- Sin tarjetas dentro de tarjetas. Un único nivel de superficie (`card`) sobre el fondo.

## Movimiento (`motion`)
- Entradas de 150–250 ms con *ease-out*; *spring* suave en los chips de intereses.
- Solo movimiento que explique un estado: algo que aparece, que "entra en antena" o que progresa. Nada decorativo en bucle salvo las ondas de audio de la landing.
- Se respeta `prefers-reduced-motion` (sin animaciones de entrada ni ondas).

## Componentes
shadcn/ui (estilo *radix-nova*, iconos Lucide) en `src/components/ui/` (código generado, excluido del lint). Clerk usa el tema `shadcn` de `@clerk/ui`, así hereda estos mismos tokens. Tema oscuro por defecto con `next-themes` (clase `.dark`).
