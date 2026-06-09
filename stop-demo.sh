#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
RUNTIME_DIR="$ROOT_DIR/.runtime"

if docker info >/dev/null 2>&1; then
  echo "Stopping local demo containers"
  docker compose down --volumes --remove-orphans --timeout 20
fi

echo "Cleaning runtime files"
rm -rf "$RUNTIME_DIR"

echo "Cleanup complete"
