"""Export the author-selected cleaned uniform set, without copying media.

Inputs are read only. The output directory must be new. This script is also
the audit trail for transforming historical server files into portable records.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import dump_json, new_output_root, sha256, write_jsonl
from realsync.manifest import Manifest, effective_offset, quantize_offset


def load(path):
    return json.loads(Path(path).read_text())


def parse_ranges(path, allowed):
    result = {}
    errors = []
    for line in Path(path).read_text().splitlines():
        fields = line.split("\t")
        clip = fields[0]
        if clip not in allowed:
            continue
        if len(fields) < 2:
            errors.append(clip)
            continue
        ranges = []
        for interval in fields[1].split():

            def seconds(text):
                minutes, seconds = text.split(":")
                return int(minutes) * 60 + float(seconds)

            start, end = map(seconds, interval.split("-"))
            ranges.append([start, end])
        result[clip] = ranges
    return result, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = new_output_root(args.output, [args.collection, args.annotations])
    provenance = []
    sources = {}
    clips = {}
    mapping = {"train": "train", "val": "test", "test": "evaluation"}
    rows_by_split = {}
    for split, historical in mapping.items():
        meta_path = (
            args.collection
            / "scripts"
            / f"full_metadata_clean_videos.target_channels.{historical}.json"
        )
        sample_path = (
            args.collection / "scripts" / f"sports_and_news_uniform.{historical}.json"
        )
        meta = load(meta_path)
        offsets = load(sample_path)
        provenance += [
            {"artifact": meta_path.name, "sha256": sha256(meta_path)},
            {"artifact": sample_path.name, "sha256": sha256(sample_path)},
        ]
        for video in meta:
            source_id = video["video_id"]
            if source_id in sources:
                raise ValueError(f"Video appears in two splits: {source_id}")
            category = video["clips"][0]["category"]
            source = {
                "source_id": source_id,
                "url": f"https://www.youtube.com/watch?v={source_id}",
                "category": category,
                "split": split,
            }
            info_dir = args.collection / "data/v5/videos" / source_id
            infos = sorted(info_dir.glob("*.info.json"))
            if infos:
                info = load(infos[0])
                source.update(
                    {
                        "source_duration_sec": info.get("duration"),
                        "historical_format_id": info.get("format_id"),
                        "historical_video_codec": info.get("vcodec"),
                        "historical_audio_codec": info.get("acodec"),
                        "historical_fps": info.get("fps"),
                    }
                )
            sources[source_id] = source
            for c in video["clips"]:
                clip_id = Path(c["path"]).stem
                suffix = clip_id[len(source_id) + 1 :].split("_")
                if len(suffix) != 2 or not all(v.isdigit() for v in suffix):
                    raise ValueError(f"Unexpected cleaned clip ID: {clip_id}")
                start, end = map(int, suffix)
                clips[clip_id] = {
                    "clip_id": clip_id,
                    "source_id": source_id,
                    "category": category,
                    "split": split,
                    "relative_path": f"{source_id}/{clip_id}.mkv",
                    "nominal_source_start_sec": start,
                    "nominal_source_end_sec": end,
                    "source_origin_sec": None,
                    "source_origin_status": "unrecovered",
                    "historical_raw_duration_sec": c["duration"],
                    "historical_track_lengths_sec": c["track_lengths"],
                }
        rows = []
        for sample_id, spec in offsets.items():
            clip_id = sample_id.rsplit("_", 2)[0]
            clip = clips[clip_id]
            start = float(spec["v_start_i_sec"])
            stored = float(spec["offset_sec"])
            offset = effective_offset(stored)
            index, label = quantize_offset(offset)
            rows.append(
                {
                    "sample_id": sample_id,
                    "source_id": clip["source_id"],
                    "clip_id": clip_id,
                    "split": split,
                    "video_start_sec": start,
                    "offset_sec": stored,
                    "effective_offset_sec": offset,
                    "offset_class": index,
                    "offset_label_sec": label,
                }
            )
        rows_by_split[split] = sorted(rows, key=lambda r: r["sample_id"])
        write_jsonl(output / f"{split}.jsonl.gz", rows_by_split[split])
        # Preserve exact historical bytes, order, and float spellings.
        legacy = output / "legacy" / f"sports_and_news_uniform.{historical}.json.gz"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        with legacy.open("wb") as raw, gzip.GzipFile(
            filename="", fileobj=raw, mode="wb", mtime=0
        ) as dest:
            dest.write(sample_path.read_bytes())
        csv_path = sample_path.with_suffix(".csv")
        provenance.append({"artifact": csv_path.name, "sha256": sha256(csv_path)})
        with (output / "legacy" / (csv_path.name + ".gz")).open("wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as dest:
                dest.write(csv_path.read_bytes())
    write_jsonl(
        output / "sources.jsonl", sorted(sources.values(), key=lambda r: r["source_id"])
    )
    write_jsonl(
        output / "clips.jsonl.gz", sorted(clips.values(), key=lambda r: r["clip_id"])
    )
    for name, label in [
        ("TALKING-HEADS.txt", "talking_head"),
        ("VOICE-OVERS.txt", "voice_over"),
    ]:
        path = args.annotations / name
        ranges, errors = parse_ranges(path, clips)
        provenance.append({"artifact": name, "sha256": sha256(path)})
        write_jsonl(
            output / "annotations" / f"{label}.jsonl.gz",
            (
                {
                    "clip_id": k,
                    "intervals_sec": ranges[k],
                    "coordinate_system": "historical_annotation_clip",
                    "status": "observed" if ranges[k] else "no_detected_intervals",
                }
                for k in sorted(ranges)
            ),
        )
    error_ids = {
        line.strip()
        for line in (args.annotations / "ERROR-FILES.txt").read_text().splitlines()
    }
    dump_json(output / "annotations" / "errors.json", sorted(error_ids & clips.keys()))
    summary = Manifest(output).audit()
    summary["annotation_coverage"] = {
        label: sum(
            1
            for _ in __import__("realsync.io", fromlist=["read_jsonl"]).read_jsonl(
                output / "annotations" / f"{label}.jsonl.gz"
            )
        )
        for label in ("talking_head", "voice_over")
    }
    summary["annotation_error_clips"] = len(error_ids & clips.keys())
    summary["nominal_hours"] = (
        sum(
            c["nominal_source_end_sec"] - c["nominal_source_start_sec"]
            for c in clips.values()
        )
        / 3600
    )
    summary["source_origin_recovered"] = 0
    dump_json(output / "summary.json", summary)
    dump_json(
        output / "provenance.json",
        {
            "selection": "author-confirmed cleaned uniform-offset set",
            "historical_split_mapping": mapping,
            "artifacts": provenance,
        },
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
