import argparse

from _foundation import validate_search_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate isolated search-data contracts")
    parser.add_argument("--production-ready", action="store_true", help="Return non-zero when setup-required production fields remain")
    args = parser.parse_args()
    raise SystemExit(validate_search_data(production_ready=args.production_ready))
