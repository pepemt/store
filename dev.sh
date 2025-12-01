#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
    echo ""
    echo "⏹ Deteniendo todos los servicios..."

    jobs -p | while read pid; do
        kill -TERM "$pid" 2>/dev/null
    done

    local timeout=5
    local count=0
    while [ $count -lt $timeout ]; do
        if ! jobs -p | grep -q .; then
            break
        fi
        sleep 1
        count=$((count + 1))
    done

    jobs -p | while read pid; do
        kill -KILL "$pid" 2>/dev/null
    done

    wait 2>/dev/null

    echo " Todos los servicios detenidos"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Iniciando entorno de desarrollo..."
echo ""

echo "[SSH] Iniciando túnel SSH..."
ssh -i ./ssh-keys/private.pem \
    -L 5000:localhost:5000 \
    -L 5432:10.0.2.182:5432 \
    -L 1522:adb.us-chicago-1.oraclecloud.com:1522 \
    -L 9000:localhost:9000 \
    -L 9001:localhost:9001 \
    -N opc@100.86.170.123 &

echo "[STRIPE] Iniciando Stripe webhook listener..."
(
    stripe listen --forward-to localhost:8000/api/v1/checkout/webhook 2>&1 | while IFS= read -r line; do
        echo "[STRIPE] $line"
        if [[ "$line" == *"whsec_"* ]]; then
            secret=$(echo "$line" | grep -oE 'whsec_[a-zA-Z0-9]+')
            if [ -n "$secret" ]; then
                if grep -q "^STRIPE_WEBHOOK_SECRET=" "$SCRIPT_DIR/.env" 2>/dev/null; then
                    sed -i '' "s/^STRIPE_WEBHOOK_SECRET=.*/STRIPE_WEBHOOK_SECRET=$secret/" "$SCRIPT_DIR/.env"
                else
                    echo "STRIPE_WEBHOOK_SECRET=$secret" >> "$SCRIPT_DIR/.env"
                fi
                echo "[STRIPE] STRIPE_WEBHOOK_SECRET actualizado en .env"
            fi
        fi
    done
) &

echo "[API] Iniciando backend..."
uv run api &

echo "[FRONTEND] Iniciando frontend..."
(cd app && npm run dev) &

echo ""
echo "Todos los servicios iniciados"
echo "Presiona Ctrl+C para detener todos los servicios"
echo ""

wait
