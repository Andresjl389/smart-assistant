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

## Registro de horas

Todas las fechas deben incluir zona horaria (`2026-10-05T08:00:00-05:00`).

| Método | Ruta | Uso |
| --- | --- | --- |
| `POST` | `/work/sessions/start` | Marca la entrada (ahora, o `started_at`). |
| `POST` | `/work/sessions/stop` | Marca la salida (`ended_at`, `break_minutes` opcionales). |
| `POST` | `/work/sessions` | Registra una jornada completa con hora de ingreso y salida. |
| `PATCH` | `/work/sessions/{id}` | Corrige ingreso, salida, descanso o nota. |
| `GET` | `/work/week?date=2026-10-08` | Resumen de la semana (lunes a domingo) de esa fecha; por defecto, la actual. |
| `GET` / `PATCH` | `/work/preferences` | Cuota semanal, zona horaria y días laborales del usuario. |

```json
POST /work/sessions
{
  "started_at": "2026-10-05T08:00:00-05:00",
  "ended_at": "2026-10-05T17:00:00-05:00",
  "break_minutes": 60,
  "note": "Oficina"
}
```

Cada jornada devuelve `duration_minutes` (salida − ingreso), `break_minutes` y
`minutes`/`hours` (tiempo neto trabajado). No se permiten jornadas que se crucen
entre sí ni de más de 24 horas.

El resumen semanal incluye horas trabajadas, cuota, lo que falta
(`remaining_minutes`), horas extra (`overtime_minutes`), porcentaje de avance,
promedio diario necesario en los días laborales restantes
(`daily_minutes_needed`) y el detalle por día con primera entrada, última salida
y diferencia frente a la meta diaria. Una jornada abierta suma hasta el momento
de la consulta, y cada jornada cuenta para el día local en que empezó.

Mientras el usuario no configure sus preferencias se usan `WORK_WEEKLY_TARGET_HOURS`
(42 h), `WORK_TIMEZONE` (`America/Bogota`) y `WORK_DAYS` (`1,2,3,4,5`, donde
1 = lunes y 7 = domingo).

## Actualizar una base existente

Ejecuta `alembic upgrade head` antes de iniciar la versión nueva. La migración
convierte los IDs de finanzas y jornadas a UUID y conserva esos registros bajo
una cuenta temporal interna. El primer usuario que se registre recibirá esos
datos; los siguientes usuarios tendrán sus propios datos aislados.
