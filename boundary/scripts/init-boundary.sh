#!/bin/sh
set -e

# ==============================================================================
# Overseer Boundary Database & Scope Initialization Script
# ==============================================================================

BOUNDARY_ADDR="${BOUNDARY_ADDR:-http://127.0.0.1:9200}"
export BOUNDARY_ADDR

echo "[*] Initializing Boundary Database Schema..."
OUTPUT=$(boundary database init -config /boundary/config/controller.hcl 2>&1) && status=0 || status=$?

if [ $status -eq 0 ]; then
    echo "$OUTPUT"
    echo "[+] Boundary Database initialized successfully."
elif echo "$OUTPUT" | grep -qiE "already initialized|schema already exists|already exists|already run|already migrated"; then
    echo "[*] Boundary database already initialized."
    echo "[+] Boundary Database schema ready."
else
    echo "[-] Boundary database initialization failed:"
    echo "$OUTPUT"
    exit $status
fi
