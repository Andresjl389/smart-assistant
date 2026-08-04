#!/usr/bin/env bash
# Arranque para produccion: aplica migraciones y levanta el servidor.
#
# La red privada de Railway (*.railway.internal) tarda unos segundos en
# quedar lista tras iniciar el contenedor. Sin reintentos, la primera
# migracion falla por DNS y el despliegue entra en bucle de reinicios.
set -euo pipefail

ATTEMPTS="${MIGRATION_ATTEMPTS:-6}"
DELAY="${MIGRATION_RETRY_DELAY:-3}"

for attempt in $(seq 1 "${ATTEMPTS}"); do
    if alembic upgrade head; then
        echo "Migraciones aplicadas."
        break
    fi

    if [ "${attempt}" -eq "${ATTEMPTS}" ]; then
        echo "Las migraciones fallaron tras ${ATTEMPTS} intentos." >&2
        exit 1
    fi

    echo "Base no disponible (intento ${attempt}/${ATTEMPTS}). Reintento en ${DELAY}s..."
    sleep "${DELAY}"
done

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
