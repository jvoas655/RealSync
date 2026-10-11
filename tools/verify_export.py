"""Prove every exported sample and its effective class matches historical input."""
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import dump_json, read_jsonl, sha256
from realsync.manifest import Manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = Manifest(args.manifests).audit()
    report["sample_roundtrip"] = {}
    for split, old in [("train", "train"), ("val", "evaluation"), ("test", "test")]:
        source = args.historical / f"sports_and_news_uniform.{old}.json"
        data = json.loads(source.read_text())
        rows = list(read_jsonl(args.manifests / f"{split}.jsonl.gz"))
        assert len(rows) == len(data)
        for r in rows:
            original = data[r["sample_id"]]
            assert original["offset_sec"] == r["offset_sec"]
            assert original["v_start_i_sec"] == r["video_start_sec"]
        archived = args.manifests / "legacy" / f"sports_and_news_uniform.{old}.json.gz"
        with gzip.open(archived, "rb") as stream:
            assert stream.read() == source.read_bytes()
        csv_source = source.with_suffix(".csv")
        with gzip.open(
            args.manifests / "legacy" / (csv_source.name + ".gz"), "rb"
        ) as stream:
            assert stream.read() == csv_source.read_bytes()
        csv_rows = list(csv.reader(io.StringIO(csv_source.read_text())))
        assert len(csv_rows) == len(data)
        seen = set()
        for sample_id, start, category in csv_rows:
            assert sample_id not in seen
            seen.add(sample_id)
            assert float(start) == data[sample_id]["v_start_i_sec"]
        assert seen == set(data)
        report["sample_roundtrip"][split] = {
            "samples": len(rows),
            "stored_values_exact": True,
            "historical_json_bytes_exact": True,
            "historical_csv_bytes_exact": True,
            "historical_sha256": sha256(source),
        }
    try:
        import numpy as np
        import torch

        torch.set_num_threads(1)
        grid = torch.from_numpy(np.linspace(-2, 2, 21)).float()
        checked = 0
        for split in ("train", "val", "test"):
            rows = list(read_jsonl(args.manifests / f"{split}.jsonl.gz"))
            for start in range(0, len(rows), 10000):
                batch = rows[start : start + 10000]
                offsets = torch.tensor(
                    [round(r["offset_sec"], 2) for r in batch], dtype=torch.float32
                )
                targets = (
                    (grid[None, :] - offsets[:, None]).abs().argmin(dim=1).tolist()
                )
                assert targets == [r["offset_class"] for r in batch]
                checked += len(batch)
        report["torch_float32_class_equivalence"] = {"samples": checked, "passed": True}
    except ImportError:
        report["torch_float32_class_equivalence"] = {
            "status": "not_run_torch_unavailable"
        }
    dump_json(args.report, report)
    print(json.dumps(report["sample_roundtrip"], indent=2))


if __name__ == "__main__":
    main()
