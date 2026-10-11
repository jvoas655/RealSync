"""Read-only reference-media inventory. No decoding or hashing of whole videos.

Save stream timing, dimensions, sizes, and leading decoded frame times for
each selected clip. Bounded concurrency limits impact on shared storage.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import read_jsonl, write_jsonl, dump_json, safe_media_path
from realsync.manifest import Manifest
from realsync.media import first_frame_pts, probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--media", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 5))
    args = parser.parse_args()
    manifest = Manifest(args.manifests)
    if args.output.exists():
        raise ValueError("Output must be new")

    def inspect(pair):
        cid, clip = pair
        path = safe_media_path(args.media, clip["relative_path"])
        if not path.is_file():
            return {"clip_id": cid, "status": "missing"}
        try:
            meta = probe(path)
            streams = []
            for s in meta["streams"]:
                streams.append(
                    {
                        k: s[k]
                        for k in (
                            "codec_type",
                            "codec_name",
                            "start_time",
                            "duration",
                            "sample_rate",
                            "channels",
                            "width",
                            "height",
                            "r_frame_rate",
                        )
                        if k in s
                    }
                )
            return {
                "clip_id": cid,
                "status": "observed",
                "size_bytes": path.stat().st_size,
                "format_duration_sec": float(meta["format"]["duration"]),
                "streams": streams,
            }
        except Exception as exc:
            return {
                "clip_id": cid,
                "status": "unreadable",
                "error_type": type(exc).__name__,
            }

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(inspect, sorted(manifest.clips.items())):
            rows.append(row)
            if len(rows) % 500 == 0:
                print(f"Indexed {len(rows)}/{len(manifest.clips)}", flush=True)
    write_jsonl(args.output, rows)
    print(json.dumps(dict(Counter(r["status"] for r in rows)), indent=2))


if __name__ == "__main__":
    main()
