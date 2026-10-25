import argparse
from pathlib import Path

from _foundation import build_integrity_manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a read-only protected website integrity manifest")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    raise SystemExit(build_integrity_manifest(args.output, args.label))
