#!/usr/bin/env bash
set -euo pipefail

echo "=== X Distribution Harness Cleanup ==="
make cleanup
make check
echo "Cleanup complete."
