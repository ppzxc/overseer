#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer Control Plane Full Bootstrap Script (Delegates to overseer.sh)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/overseer.sh" start all
