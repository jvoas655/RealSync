"""Frozen samples; historical continuous offsets are retained without resampling."""
from collections import Counter
import struct
from pathlib import Path
from .io import read_jsonl


def quantize_offset(offset_sec):
    """Match historical float32 torch grid subtraction, including boundary ties."""

    def f32(value):
        return struct.unpack("f", struct.pack("f", value))[0]

    offset = f32(float(offset_sec))
    grid = [f32(i / 5) for i in range(-10, 11)]
    index = min(range(21), key=lambda i: abs(f32(grid[i] - offset)))
    return index, grid[index]


def effective_offset(offset_sec):
    # The historical fixed-offset transform rounds the stored float to 2 decimals.
    return round(float(offset_sec), 2)


class Manifest:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.sources = {
            r["source_id"]: r for r in read_jsonl(self.directory / "sources.jsonl")
        }
        self.clips = {
            r["clip_id"]: r for r in read_jsonl(self.directory / "clips.jsonl.gz")
        }

    def samples(self, split):
        if split not in ("train", "val", "test"):
            raise ValueError("Split must be train, val, or test")
        yield from read_jsonl(self.directory / f"{split}.jsonl.gz")

    def audit(self):
        split_sources = {}
        split_samples = {}
        summary = {}
        for split in ("train", "val", "test"):
            ids = set()
            sources = set()
            classes = Counter()
            for r in self.samples(split):
                if r["sample_id"] in ids:
                    raise ValueError(f'Duplicate sample ID: {r["sample_id"]}')
                ids.add(r["sample_id"])
                clip = self.clips[r["clip_id"]]
                if clip["split"] != split or clip["source_id"] != r["source_id"]:
                    raise ValueError(f'Split/source inconsistency: {r["sample_id"]}')
                if r["source_id"] not in self.sources or not -2 <= r["offset_sec"] <= 2:
                    raise ValueError(f'Invalid source/offset: {r["sample_id"]}')
                index, _ = quantize_offset(effective_offset(r["offset_sec"]))
                if index != r["offset_class"]:
                    raise ValueError(f'Wrong class: {r["sample_id"]}')
                sources.add(r["source_id"])
                classes[index] += 1
            split_sources[split], split_samples[split] = sources, ids
            summary[split] = {
                "samples": len(ids),
                "sources": len(sources),
                "classes": dict(sorted(classes.items())),
            }
        for a, b in [("train", "val"), ("train", "test"), ("val", "test")]:
            if (
                split_sources[a] & split_sources[b]
                or split_samples[a] & split_samples[b]
            ):
                raise ValueError(f"Split overlap: {a}/{b}")
        return {
            "sources": len(self.sources),
            "clips": len(self.clips),
            "splits": summary,
        }
