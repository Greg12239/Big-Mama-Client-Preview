from __future__ import annotations

import argparse
import json

from _phase3b import build_phase3b, write_final_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build isolated Phase 3B search activation evidence")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    print(json.dumps(write_final_report() if args.finalize else build_phase3b(), sort_keys=True))

