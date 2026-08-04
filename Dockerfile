# Nixpacks no puede construir este proyecto: su imagen base es anterior a
# Python 3.14 y el uv que instala tampoco sabe descargarlo. Con una imagen
# oficial fijamos el mismo interprete que se usa en desarrollo.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.29

# Las dependencias se instalan antes de copiar el codigo para que la capa
# quede cacheada mientras pyproject.toml y uv.lock no cambien.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["bash", "scripts/start.sh"]
