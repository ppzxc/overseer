#!/usr/bin/env bash
set -e

# Overseer Services Healthcheck Script
echo "[*] Checking Overseer Services Health..."

echo -n "1. PostgreSQL: "
if docker compose exec -T postgres pg_isready -U boundary >/dev/null 2>&1; then
    echo "HEALTHY"
else
    echo "UNHEALTHY"
fi

echo -n "2. Vault API (8200): "
if curl -s http://127.0.0.1:8200/v1/sys/health >/dev/null 2>&1 || [ $? -eq 2 ]; then
    echo "HEALTHY"
else
    echo "UNHEALTHY / DOWN"
fi

echo -n "3. Boundary Controller (9200): "
if curl -s http://127.0.0.1:9200/v1/health >/dev/null 2>&1; then
    echo "HEALTHY"
else
    echo "STARTING / UNHEALTHY"
fi

echo -n "4. Prometheus (9090): "
if curl -s http://127.0.0.1:9090/-/healthy >/dev/null 2>&1; then
    echo "HEALTHY"
else
    echo "UNHEALTHY / DOWN"
fi
