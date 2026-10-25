#!/usr/bin/env bash
set -euo pipefail

echo "Checking current files against approved baseline..."
for f in index.html styles.css app.js README.md; do
  if [ -f "$f" ] && [ -f ".approved-baseline/$f" ]; then
    echo ""
    echo "==== $f ===="
    diff -u ".approved-baseline/$f" "$f" || true
  fi
done
