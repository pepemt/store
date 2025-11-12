# ============================================================================
# Stage 1: Build Frontend (React + Vite)
# ============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build/app

# Copiar archivos de dependencias para aprovechar cache de Docker
COPY app/package*.json ./
RUN npm ci --prefer-offline --no-audit

# Copiar código fuente y hacer build
COPY app/ ./
RUN npm run build

# ============================================================================
# Stage 2: Setup Python Environment with uv
# ============================================================================
FROM python:3.12-slim AS python-builder

# Instalar uv desde la imagen oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copiar archivos de configuración del workspace
COPY pyproject.toml uv.lock ./

# Copiar los módulos necesarios (api, database, images, text)
COPY api/ ./api/
COPY database/ ./database/
COPY images/ ./images/
COPY text/ ./text/

# Sincronizar dependencias usando uv (sin dev dependencies)
# --frozen: usa uv.lock sin actualizar
# --no-dev: no instala dependencias de desarrollo
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev

# ============================================================================
# Stage 3: Final Runtime Image
# ============================================================================
FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar el virtualenv completo con todas las dependencias
COPY --from=python-builder /build/.venv /app/.venv

# Copiar los módulos de Python
COPY --from=python-builder /build/api /app/api
COPY --from=python-builder /build/database /app/database
COPY --from=python-builder /build/images /app/images
COPY --from=python-builder /build/text /app/text
COPY --from=python-builder /build/pyproject.toml /app/pyproject.toml

# Copiar el build del frontend al directorio static de la API
COPY --from=frontend-builder /build/app/api/src/static /app/api/src/static

# Configurar PATH para usar el virtualenv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Exponer puerto de la API
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Ejecutar la aplicación usando uvicorn directamente
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
