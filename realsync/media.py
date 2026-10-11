"""CPU media processing. Inputs are read-only; outputs never overwrite files."""
import json
from pathlib import Path
import subprocess

from .io import new_output_root, dump_json, safe_media_path, sha256


def probe(path, ffprobe="ffprobe"):
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(result.stdout)


def first_frame_pts(path, stream, ffprobe="ffprobe"):
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            stream,
            "-read_intervals",
            "%+#16",
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    frames = json.loads(result.stdout)["frames"]
    if not frames:
        raise ValueError(f"No decoded {stream} frames: {path}")
    return float(frames[0]["best_effort_timestamp_time"])


def validate_format(path, ffprobe="ffprobe"):
    data = probe(path, ffprobe)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next(s for s in data["streams"] if s["codec_type"] == "audio")
    problems = []
    for ok, description in [
        (video["codec_name"] == "h264", "video must be H.264"),
        (video["r_frame_rate"] == "25/1", "video must be 25 fps"),
        (min(video["width"], video["height"]) == 256, "shortest side must be 256"),
        (audio["codec_name"] == "aac", "audio must be AAC"),
        (int(audio["sample_rate"]) == 16000, "audio must be 16 kHz"),
        (audio["channels"] == 1, "audio must be mono"),
    ]:
        if not ok:
            problems.append(description)
    return data, problems


def prepare(
    manifest,
    input_root,
    output_root,
    kind,
    *,
    clip_ids=None,
    ffmpeg="ffmpeg",
    ffprobe="ffprobe",
    encoder_threads=2,
):
    """Port of recovered reencode + stream-copy crop commands.

    full-sources requires recovered origins, not nominal filename boundaries.
    No guessed original-video timeline is ever used.
    """
    input_root = Path(input_root).resolve()
    if not 1 <= encoder_threads <= 16:
        raise ValueError("Encoder threads must be between 1 and 16")
    selected = sorted(clip_ids if clip_ids is not None else manifest.clips)
    if kind == "full-sources":
        unknown = [
            c for c in selected if manifest.clips[c]["source_origin_sec"] is None
        ]
        if unknown:
            raise ValueError(
                f"{len(unknown)} clips lack recovered original-source origins. Full-source reconstruction is blocked; nominal filename times are not a substitute. See docs/REPRODUCIBILITY.md."
            )
    output = new_output_root(output_root, [input_root, manifest.directory])
    version = subprocess.check_output([ffmpeg, "-version"], text=True).splitlines()[0]
    records = []
    for clip_id in selected:
        clip = manifest.clips[clip_id]
        if kind == "full-sources":
            candidates = [
                input_root / (clip["source_id"] + ext)
                for ext in (".mkv", ".mp4", ".webm")
            ]
            existing = [p for p in candidates if p.is_file()]
            if len(existing) != 1:
                raise ValueError(
                    f'Expected one full source file for {clip["source_id"]}'
                )
            source = existing[0]
        else:
            source = safe_media_path(input_root, clip["relative_path"])
        if not source.is_file():
            records.append({"clip_id": clip_id, "status": "missing_input"})
            continue
        destination = safe_media_path(output, clip["relative_path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        intermediate = destination.with_suffix(".encoded.mkv")
        cmd = []
        if kind == "encoded-segments":
            intermediate = source
        else:
            cmd = [
                ffmpeg,
                "-nostdin",
                "-n",
                "-hide_banner",
                "-loglevel",
                "error",
                "-threads",
                "2",
                "-i",
                str(source),
            ]
            if kind == "full-sources":
                cmd += [
                    "-ss",
                    str(clip["source_origin_sec"]),
                    "-t",
                    str(clip["historical_raw_duration_sec"]),
                ]
            cmd += [
                "-max_muxing_queue_size",
                "2048",
                "-vf",
                "fps=25,scale=iw*256/min(iw\,ih):ih*256/min(iw\,ih),crop=trunc(iw/2)*2:trunc(ih/2)*2",
                "-vcodec",
                "libx264",
                "-threads",
                str(encoder_threads),
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "10",
                "-acodec",
                "aac",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(intermediate),
            ]
            subprocess.run(cmd, check=True)
        start = max(
            first_frame_pts(intermediate, "v:0", ffprobe),
            first_frame_pts(intermediate, "a:0", ffprobe),
        )
        crop = [
            ffmpeg,
            "-nostdin",
            "-n",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(intermediate),
            "-ss",
            str(start),
            "-reset_timestamps",
            "1",
            "-c",
            "copy",
            str(destination),
        ]
        subprocess.run(crop, check=True)
        # Keep the intermediate: useful for auditing, and never delete input data.
        info, problems = validate_format(destination, ffprobe)
        records.append(
            {
                "clip_id": clip_id,
                "status": "format_ok" if not problems else "invalid_format",
                "problems": problems,
                "input_sha256": sha256(source),
                "output_sha256": sha256(destination),
                "first_frame_crop_sec": start,
                "encode_command": cmd,
                "crop_command": crop,
                "duration_sec": float(info["format"]["duration"]),
            }
        )
        dump_json(
            output / "preparation.json",
            {
                "recipe": "recovered-reencode-and-stream-copy-crop",
                "ffmpeg": version,
                "input_kind": kind,
                "records": records,
            },
        )
    dump_json(
        output / "preparation.json",
        {
            "recipe": "recovered-reencode-and-stream-copy-crop",
            "ffmpeg": version,
            "input_kind": kind,
            "records": records,
        },
    )
    return output
