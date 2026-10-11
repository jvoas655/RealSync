"""Command-line audit, preparation, and strict availability reporting."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

from .io import dump_json, safe_media_path, sha256
from .manifest import Manifest
from .media import prepare, validate_format


def validate(manifest, media_root, output, *, workers=2, deep=False):
    """Validate files without modifying them; outputs belong in a separate root."""
    media_root = Path(media_root).resolve()
    output = Path(output).resolve()
    if output.is_relative_to(media_root) or output.exists():
        raise ValueError("Report must be a new file outside the media directory")

    def check(row):
        clip_id, row = row
        path = safe_media_path(media_root, row["relative_path"])
        record = {"clip_id": clip_id, "status": "missing"}
        if path.is_file():
            record["size_bytes"] = path.stat().st_size
            if not deep:
                record["status"] = "present_unverified"
            else:
                try:
                    info, problems = validate_format(path)
                    record.update(
                        status="invalid_format" if problems else "format_ok",
                        problems=problems,
                        duration_sec=float(info["format"]["duration"]),
                        sha256=sha256(path),
                    )
                    if (
                        row.get("reference_sha256")
                        and record["sha256"] != row["reference_sha256"]
                    ):
                        record["status"] = "reference_mismatch"
                except Exception as exc:
                    record.update(status="unreadable", error=str(exc))
        return record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        clips = list(pool.map(check, sorted(manifest.clips.items())))
    by_clip = {r["clip_id"]: r for r in clips}
    available = {}
    for split in ("train", "val", "test"):
        available[split] = [
            r["sample_id"]
            for r in manifest.samples(split)
            if by_clip[r["clip_id"]]["status"] in ("present_unverified", "format_ok")
        ]
    result = {
        "depth": "format_and_hash" if deep else "presence_only",
        "clips": clips,
        "available_ids": available,
        "available_sample_counts": {k: len(v) for k, v in available.items()},
        "warning": "Presence or format checks alone do not prove source timeline equivalence; strict reads may still reject short windows.",
    }
    dump_json(output, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog="realsync")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser(
        "audit", help="Check manifests, frozen labels, and split separation"
    )
    audit.add_argument("--manifests", type=Path, required=True)
    val = sub.add_parser(
        "validate", help="Write a report; never replace missing examples"
    )
    val.add_argument("--manifests", type=Path, required=True)
    val.add_argument("--media", type=Path, required=True)
    val.add_argument("--report", type=Path, required=True)
    val.add_argument("--deep", action="store_true")
    val.add_argument("--workers", type=int, choices=range(1, 9), default=2)
    prep = sub.add_parser(
        "prepare", help="Re-encode and crop researcher-provided inputs"
    )
    prep.add_argument("--manifests", type=Path, required=True)
    prep.add_argument("--input", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument(
        "--input-kind",
        choices=["raw-segments", "encoded-segments", "full-sources"],
        required=True,
    )
    prep.add_argument("--clip-id", action="append")
    ev = sub.add_parser(
        "evaluate", help="Score one prediction per explicitly evaluated sample ID"
    )
    ev.add_argument("--manifests", type=Path, required=True)
    ev.add_argument("--predictions", type=Path, required=True)
    ev.add_argument("--split", choices=["train", "val", "test"], default="test")
    ev.add_argument(
        "--subset",
        type=Path,
        help="JSON list of evaluated sample IDs; required for partial coverage",
    )
    args = parser.parse_args(argv)
    try:
        manifest = Manifest(args.manifests)
        if args.command == "audit":
            print(json.dumps(manifest.audit(), indent=2))
        elif args.command == "validate":
            result = validate(
                manifest, args.media, args.report, workers=args.workers, deep=args.deep
            )
            print(json.dumps(result["available_sample_counts"], indent=2))
        elif args.command == "prepare":
            print(
                prepare(
                    manifest,
                    args.input,
                    args.output,
                    args.input_kind,
                    clip_ids=args.clip_id,
                )
            )
        elif args.command == "evaluate":
            from .evaluation import evaluate

            expected = json.loads(args.subset.read_text()) if args.subset else None
            print(
                json.dumps(
                    evaluate(manifest, args.predictions, args.split, expected), indent=2
                )
            )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
