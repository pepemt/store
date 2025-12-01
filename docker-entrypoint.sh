#!/bin/bash
set -e

if [ -n "$OCI_USER" ] && [ -n "$OCI_FINGERPRINT" ] && [ -n "$OCI_TENANCY" ] && [ -n "$OCI_REGION" ]; then
    echo "Generating OCI config from environment variables..."

    mkdir -p /root/.oci

    cat > /root/.oci/config << EOF
[DEFAULT]
user=${OCI_USER}
fingerprint=${OCI_FINGERPRINT}
key_file=${OCI_KEY_FILE:-/root/.oci/private.pem}
tenancy=${OCI_TENANCY}
region=${OCI_REGION}
EOF

    chmod 600 /root/.oci/config

    if [ ! -f "${OCI_KEY_FILE:-/root/.oci/private.pem}" ]; then
        echo "WARNING: OCI private key not found at ${OCI_KEY_FILE:-/root/.oci/private.pem}"
        echo "Mount your private key as a volume, e.g.:"
        echo "  -v /path/to/private.pem:/root/.oci/private.pem:ro"
    else
        echo "OCI config generated successfully"
    fi
else
    echo "OCI environment variables not set, skipping OCI config generation"
fi

exec "$@"
