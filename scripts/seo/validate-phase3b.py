from __future__ import annotations

import argparse
import json

from _phase3b import validate_phase3b


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate isolated Phase 3B outputs")
    parser.add_argument("--complete", action="store_true", help="Require determinism and final protected-file comparison")
    args = parser.parse_args()
    result = validate_phase3b(require_determinism=args.complete, require_integrity=args.complete)
    print(json.dumps({"status": result["status"], **result["tests"]}, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 2)

