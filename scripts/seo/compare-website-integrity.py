import argparse
from pathlib import Path

from _foundation import compare_integrity

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare protected website integrity manifests")
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(compare_integrity(args.before, args.after, args.output))
