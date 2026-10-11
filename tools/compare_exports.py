"""Compare a fresh metadata export with a frozen release byte for byte."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import dump_json, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--rebuilt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for source in sorted(args.rebuilt.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(args.rebuilt)
        reference = args.reference / relative
        record = {
            "artifact": str(relative),
            "rebuilt_sha256": sha256(source),
            "reference_sha256": sha256(reference),
        }
        record["exact"] = record["rebuilt_sha256"] == record["reference_sha256"]
        records.append(record)
    if not records or not all(row["exact"] for row in records):
        raise ValueError("Metadata rebuild differs from frozen export")
    dump_json(args.report, {"artifacts": records, "all_exact": True})
    print(f"{len(records)} rebuilt artifacts match byte for byte")


if __name__ == "__main__":
    main()
