from __future__ import annotations

import argparse
import json

from _phase3 import build_phase3, write_final_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build isolated Phase 3A SEO/GEO/AEO evidence")
    parser.add_argument("--finalize", action="store_true", help="Refresh the final report from completed validation evidence")
    args = parser.parse_args()
    result = write_final_report() if args.finalize else build_phase3()
    print(json.dumps(result, sort_keys=True))
