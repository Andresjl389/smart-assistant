# Smart Assistant

API para finanzas, registro de horas y organización de correo.

## Autenticación

`POST /auth/register` crea una cuenta y `POST /auth/login` inicia sesión. Ambos
devuelven el usuario y guardan una cookie `HttpOnly`; usa `POST /auth/logout`
para revocarla y `GET /auth/me` para consultar la sesión actual. Los endpoints
de `/finance` y `/work` requieren esa cookie.
Las rutas de procesamiento y configuración de Gmail también requieren sesión.
El callback entrante `/webhooks/gmail` verifica el token OIDC de Pub/Sub:
configura `GMAIL_WEBHOOK_AUDIENCE`, `GMAIL_WEBHOOK_SERVICE_ACCOUNT` y la
autenticación OIDC de la suscripción push con esa misma audiencia e identidad.

Envía JSON con `email` y `password` (mínimo 8 caracteres). En clientes web,
habilita el envío de credenciales (`credentials: "include"`) y configura
`CORS_ORIGINS` con el origen exacto del frontend. En desarrollo sobre HTTP
local, configura `AUTH_COOKIE_SECURE=false`; en producción debe permanecer
`true` y la API debe servirse por HTTPS.

## Actualizar una base existente

Ejecuta `alembic upgrade head` antes de iniciar la versión nueva. La migración
convierte los IDs de finanzas y jornadas a UUID y conserva esos registros bajo
una cuenta temporal interna. El primer usuario que se registre recibirá esos
datos; los siguientes usuarios tendrán sus propios datos aislados.
