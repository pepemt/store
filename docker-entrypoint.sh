#!/bin/bash
set -e

echo "🔧 Configurando entorno Docker..."

# Arreglar rutas en el archivo de configuración OCI
if [ -f "/root/.oci/config" ]; then
    echo "📝 Ajustando rutas en /root/.oci/config..."

    # Crear directorio temporal para config modificado
    mkdir -p /tmp/.oci

    # Copiar y ajustar el config file
    sed 's|/Users/[^/]*/\.oci/|/root/.oci/|g; s|~/\.oci/|/root/.oci/|g' /root/.oci/config > /tmp/.oci/config

    # Copiar otros archivos necesarios (keys)
    cp /root/.oci/*.pem /tmp/.oci/ 2>/dev/null || true

    # Actualizar variable de entorno para que OCI SDK use el config modificado
    export OCI_CONFIG_FILE=/tmp/.oci/config

    echo "✅ Configuración OCI ajustada (usando $OCI_CONFIG_FILE)"
else
    echo "⚠️  Advertencia: /root/.oci/config no encontrado"
    echo "   Asegúrate de montar el volumen: -v ~/.oci:/root/.oci:ro"
fi

# Verificar que el wallet existe
if [ ! -d "$ORACLE_WALLET_LOCATION" ]; then
    echo "⚠️  Advertencia: Oracle wallet no encontrado en $ORACLE_WALLET_LOCATION"
    echo "   Asegúrate de montar el volumen: -v $(pwd)/.data/adb-wallet:/app/.data/adb-wallet:ro"
fi

echo "🚀 Iniciando aplicación..."

# Ejecutar el comando pasado al contenedor
exec "$@"
