"""Build a deterministic metadata-only release asset from tracked files."""
import argparse
import gzip
import io
from pathlib import Path
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    names = (
        subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
        .decode()
        .split("\0")
    )
    selected = sorted(
        name for name in names if name.startswith(("manifests/", "validation/"))
    )
    if args.output.exists():
        raise ValueError("Output archive must be new")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as raw, gzip.GzipFile(
        filename="", fileobj=raw, mode="wb", mtime=0
    ) as zipped:
        with tarfile.open(
            fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            for name in selected:
                payload = (root / name).read_bytes()
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                info.mode = 0o644
                info.mtime = 0
                info.uid = info.gid = 0
                archive.addfile(info, io.BytesIO(payload))
    print(
        f"Metadata-only archive: {len(selected)} files, {args.output.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
