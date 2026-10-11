"""Compare a frozen sample's decoded arrays from two prepared media roots."""
import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import dump_json, safe_media_path
from realsync.loader import read_window
from realsync.manifest import Manifest


def main():
    import numpy as np

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--rebuilt", type=Path, required=True)
    parser.add_argument("--clip-id", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = Manifest(args.manifests)
    clip = manifest.clips[args.clip_id]
    row = next(
        r
        for r in manifest.samples(clip["split"])
        if r["clip_id"] == args.clip_id and r["video_start_sec"] == 20
    )
    path_a = safe_media_path(args.reference, clip["relative_path"])
    path_b = safe_media_path(args.rebuilt, clip["relative_path"])
    video_a, audio_a = read_window(path_a, row["video_start_sec"], row["offset_sec"])
    video_b, audio_b = read_window(path_b, row["video_start_sec"], row["offset_sec"])
    repeat_v, repeat_a = read_window(path_b, row["video_start_sec"], row["offset_sec"])
    np.testing.assert_array_equal(video_b, repeat_v)
    np.testing.assert_array_equal(audio_b, repeat_a)
    result = {
        "sample_id": row["sample_id"],
        "video_start_sec": row["video_start_sec"],
        "stored_offset_sec": row["offset_sec"],
        "frames": len(video_a),
        "audio_samples": len(audio_a),
        "repeat_read_exact": True,
        "video_exact": bool(np.array_equal(video_a, video_b)),
        "audio_exact": bool(np.array_equal(audio_a, audio_b)),
        "mean_absolute_video_difference_0_255": float(
            np.mean(np.abs(video_a.astype("int16") - video_b.astype("int16")))
        ),
        "audio_rms_difference": float(
            np.sqrt(
                np.mean((audio_a.astype("float64") - audio_b.astype("float64")) ** 2)
            )
        ),
        "reference_video_sha256": hashlib.sha256(video_a.tobytes()).hexdigest(),
        "rebuilt_video_sha256": hashlib.sha256(video_b.tobytes()).hexdigest(),
        "reference_audio_sha256": hashlib.sha256(audio_a.tobytes()).hexdigest(),
        "rebuilt_audio_sha256": hashlib.sha256(audio_b.tobytes()).hexdigest(),
    }
    dump_json(args.report, result)
    print(result)


if __name__ == "__main__":
    main()
