"""Fail a publication check if non-allowlisted or media files are staged.

Checks only the new release checkout, never modifies data or git history.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    names = (
        subprocess.check_output(["git", "-C", str(args.root), "ls-files", "-z"])
        .decode()
        .split("\0")
    )
    allowed = {
        ".gitignore",
        "README.md",
        "LICENSE",
        "DATA_LICENSE.md",
        "CITATION.cff",
        "pyproject.toml",
        "SHA256SUMS",
        "requirements-reference.txt",
    }
    prefixes = (
        "realsync/",
        "tools/",
        "tests/",
        "docs/",
        "manifests/",
        "validation/",
        ".github/workflows/",
    )
    count = 0
    for name in filter(None, names):
        if name not in allowed and not name.startswith(prefixes):
            raise ValueError(f"Unexpected staged file: {name}")
        path = args.root / name
        if (
            path.suffix.lower()
            in {".mkv", ".mp4", ".wav", ".mp3", ".webm", ".jpg", ".png", ".pt", ".pkl"}
            or "__pycache__" in name
        ):
            raise ValueError(f"Media/binary excluded: {name}")
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError(f"Unexpectedly large file: {name}")
        if name.startswith("manifests/"):
            data = (
                gzip.decompress(path.read_bytes())
                if path.suffix == ".gz"
                else path.read_bytes()
            )
            text = data.decode("utf-8")
            if any(
                token in text
                for token in (
                    "/home/",
                    "/saltpool",
                    "s3://",
                    "http_headers",
                    "googlevideo.com",
                )
            ):
                raise ValueError(
                    f"Nonportable or acquisition-internal metadata: {name}"
                )
        count += 1
    if not count:
        raise ValueError("No tracked files to validate")
    print(
        f"Publication file check passed: {count} files; no media or acquisition credentials"
    )


if __name__ == "__main__":
    main()
