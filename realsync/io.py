"""Portable release I/O; input files are only ever opened for reading."""
import gzip
import hashlib
import json
from pathlib import Path


def read_jsonl(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path, rows):
    """Stable bytes, including gzip header timestamps, for release rebuilds."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        with path.open("wb") as raw, gzip.GzipFile(
            filename="", fileobj=raw, mode="wb", mtime=0
        ) as stream:
            for row in rows:
                stream.write(
                    (
                        json.dumps(
                            row, sort_keys=True, separators=(",", ":"), allow_nan=False
                        )
                        + "\n"
                    ).encode()
                )
    else:
        with path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(
                    json.dumps(
                        row, sort_keys=True, separators=(",", ":"), allow_nan=False
                    )
                    + "\n"
                )


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def safe_media_path(root, relative_path):
    root = Path(root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes media root: {relative_path}")
    return path


def new_output_root(output, inputs):
    """Refuse outputs within inputs or a pre-existing directory; never overwrite."""
    output = Path(output).resolve()
    for input_root in inputs:
        input_root = Path(input_root).resolve()
        if output.is_relative_to(input_root) or input_root.is_relative_to(output):
            raise ValueError(
                "Output and input roots must be separate, non-overlapping directories"
            )
    output.mkdir(parents=True, exist_ok=False)
    return output
