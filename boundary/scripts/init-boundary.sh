#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer Boundary Database & Scope Initialization Script
# ==============================================================================

BOUNDARY_ADDR="${BOUNDARY_ADDR:-http://127.0.0.1:9200}"
export BOUNDARY_ADDR

echo "[*] Initializing Boundary Database Schema..."
boundary database init -config /boundary/config/controller.hcl || echo "[*] Boundary database already initialized."

echo "[+] Boundary Database initialized successfully."
