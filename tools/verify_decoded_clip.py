"""Compare all decoded RGB and float32 PCM without buffering a whole clip."""
import argparse
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import dump_json, safe_media_path
from realsync.manifest import Manifest


def fingerprint(path, kind):
    command = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-threads",
        "1",
        "-filter_threads",
        "1",
        "-i",
        str(path),
    ]
    if kind == "video":
        command += [
            "-map",
            "0:v:0",
            "-an",
            "-vsync",
            "0",
            "-c:v",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-threads",
            "1",
        ]
    else:
        command += ["-map", "0:a:0", "-vn", "-c:a", "pcm_f32le"]
    command += ["-f", "hash", "-hash", "SHA256", "pipe:1"]
    return (
        subprocess.check_output(command, text=True, timeout=600).strip().split("=")[-1]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--rebuilt", type=Path, required=True)
    parser.add_argument("--clip-id", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    clip = Manifest(args.manifests).clips[args.clip_id]
    paths = {
        "reference": safe_media_path(args.reference, clip["relative_path"]),
        "rebuilt": safe_media_path(args.rebuilt, clip["relative_path"]),
    }
    result = {
        "clip_id": args.clip_id,
        "scope": "all decoded frames/audio; container metadata bytes excluded",
    }
    for kind in ("video", "audio"):
        values = {name: fingerprint(path, kind) for name, path in paths.items()}
        result[kind] = values
        result[kind + "_exact"] = values["reference"] == values["rebuilt"]
    dump_json(args.report, result)
    print(result)


if __name__ == "__main__":
    main()
