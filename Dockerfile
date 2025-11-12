# ============================================================================
# Stage 1: Build Frontend (React + Vite)
# ============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build/app

# Copiar archivos de dependencias para aprovechar cache de Docker
COPY app/package*.json ./
RUN npm ci --prefer-offline --no-audit

# Copiar código fuente del frontend
COPY app/ ./

# Sobrescribir vite.config.ts para usar output por defecto (dist/)
RUN printf '%s\n' \
    "import { defineConfig } from 'vite'" \
    "import react from '@vitejs/plugin-react'" \
    "import path from 'path'" \
    "" \
    "export default defineConfig({" \
    "  plugins: [react()]," \
    "  resolve: {" \
    "    alias: {" \
    "      '@': path.resolve(__dirname, './src')," \
    "    }," \
    "  }," \
    "  build: {" \
    "    outDir: 'dist'," \
    "    emptyOutDir: true," \
    "  }," \
    "})" \
    > vite.config.ts

# Hacer build del frontend (output: ./dist/)
RUN npm run build

# ============================================================================
# Stage 2: Setup Python Environment with uv
# ============================================================================
FROM python:3.12-slim AS python-builder

# Instalar uv desde la imagen oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Instalar herramientas de compilación necesarias para paquetes con extensiones C
# (solo en build stage, no en runtime)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copiar archivos de configuración del workspace
COPY pyproject.toml uv.lock ./

# Copiar TODOS los módulos del workspace (necesarios para uv.lock)
COPY api/ ./api/
COPY database/ ./database/
COPY images/ ./images/
COPY text/ ./text/
COPY ML/ ./ML/
COPY initialization/ ./initialization/

# Sincronizar dependencias usando uv
# --frozen: usa uv.lock sin actualizar
# --no-dev: no instala dependency-groups dev
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

# Instalar uv en runtime para reinstalar paquetes locales
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar el virtualenv completo con todas las dependencias
COPY --from=python-builder /build/.venv /app/.venv

# Copiar los módulos de Python
COPY --from=python-builder /build/api /app/api
COPY --from=python-builder /build/database /app/database
COPY --from=python-builder /build/images /app/images
COPY --from=python-builder /build/text /app/text
COPY --from=python-builder /build/pyproject.toml /app/pyproject.toml
COPY --from=python-builder /build/uv.lock /app/uv.lock

# Copiar el build del frontend al directorio static de la API
COPY --from=frontend-builder /build/app/dist /app/api/src/static

# Copiar Oracle wallet y configuración OCI (si existen)
# Wallet de Oracle para conexión a base de datos
COPY .data/adb-wallet /app/.data/adb-wallet

# Configuración OCI
# IMPORTANTE: Antes del build, copiar ~/.oci al directorio del proyecto:
#   cp -r ~/.oci .
# O en producción, montar como volume/secret
RUN mkdir -p /root/.oci
COPY .oci/ /root/.oci/

# Configurar PATH para usar el virtualenv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Variable de entorno para el wallet
ENV ORACLE_WALLET_LOCATION=/app/.data/adb-wallet

# Reinstalar los paquetes locales en sus ubicaciones finales
RUN uv pip install --no-deps -e /app/api -e /app/database -e /app/images -e /app/text

# Exponer puerto de la API
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Ejecutar la aplicación usando python -m uvicorn
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
