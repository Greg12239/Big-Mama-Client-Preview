#!/usr/bin/env bash
set -euo pipefail

echo "Restoring approved baseline files..."
if [ ! -d ".approved-baseline" ]; then
  echo "ERROR: .approved-baseline folder not found."
  exit 1
fi

for f in index.html styles.css app.js README.md; do
  if [ -f ".approved-baseline/$f" ]; then
    cp ".approved-baseline/$f" "$f"
    echo "Restored $f"
  fi
done

echo "Done. Review the site before committing."
