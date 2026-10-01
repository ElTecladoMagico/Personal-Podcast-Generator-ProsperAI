# 0005 · Autenticación: Clerk

**Estado:** Aceptada

## Contexto
Varios usuarios con cuentas propias y un rol de administrador para el dashboard interno. La autenticación no es lo que se evalúa: debe costar el mínimo código posible y verse profesional.

## Decisión
**Clerk**: componentes ya hechos `<SignIn/>` y `<UserButton/>` en React. El backend verifica el JWT con las claves públicas (JWKS) de Clerk, sin llamadas por petición. Rol admin en `publicMetadata.role = "admin"`.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **Clerk (elegida)** | Gratis hasta 50.000 usuarios retenidos/mes. UI de login lista y bonita. Google/GitHub/email sin código. JWT estándar. | Dependencia de un tercero (sin autoalojamiento). Los usuarios viven fuera de nuestra BD: guardamos su `clerk_id`. |
| Firebase Auth | Gratis, tienes cuenta | UI menos pulida (FirebaseUI está en desuso). Verificar tokens en Python requiere `firebase-admin`. |
| Auth.js / FastAPI-Users | Sin terceros | Mucho más código propio y seguridad a nuestro cargo (hash, reseteo de contraseña, emails) |
| Supabase Auth | Gratis | Nos acoplaría a Supabase como BD |
| Auth0 | Maduro | Más configuración. Capa gratuita menor. |

## Consecuencias
- Al primer acceso autenticado creamos la fila en `users` (*upsert* por `clerk_id`).
- El RSS privado no puede usar JWT (las apps de podcasts no lo envían): usa un **token secreto en la URL** del feed, revocable. Ver [0011](0011-entrega-rss-privado.md).

## Configuración reproducible con el CLI de Clerk (añadido 2026-10-01)
La configuración de la instancia no se hace con clics en el dashboard sino con el [CLI de Clerk](https://clerk.com/docs/cli): `clerk link` enlaza el repo con la app, `clerk config patch` fija los *custom claims* del token y `clerk env pull` obtiene las claves. Así queda documentado en el README y se puede repetir (por ejemplo, para la instancia de producción).

| Opción | Pros | Contras |
|---|---|---|
| **CLI (elegida)** | Reproducible, versionable como comando, sin pasos manuales | Una herramienta más que instalar (`npm i -g clerk`) |
| Dashboard web | Sin instalar nada | Pasos manuales fáciles de olvidar u omitir al pasar a producción |

El backend **no usa la Secret key**: solo verifica tokens con el JWKS público. La Secret key no se guarda en ningún fichero del proyecto.
