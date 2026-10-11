"""Strict, deterministic timeline reader; optional numpy, no torch dependency.

This reference view uses manifest positions directly. It is NOT a replacement
claim for the historical torchvision reader, which had additional seek/slice
and fallback behavior. See docs/REPRODUCIBILITY.md.
"""
import subprocess
from .io import safe_media_path
from .manifest import Manifest, effective_offset
from .media import probe


def read_window(
    path,
    video_start_sec,
    offset_sec,
    duration_sec=5,
    ffmpeg="ffmpeg",
    ffprobe="ffprobe",
):
    import numpy as np

    start = float(video_start_sec)
    audio_start = start + effective_offset(offset_sec)
    if min(start, audio_start) < 0 or duration_sec <= 0:
        raise ValueError("Window starts must be nonnegative and duration positive")
    info = probe(path, ffprobe)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    if v["r_frame_rate"] != "25/1" or a["sample_rate"] != "16000" or a["channels"] != 1:
        raise ValueError("Reader requires prepared 25 fps / 16 kHz mono inputs")
    w, h = v["width"], v["height"]
    base = [ffmpeg, "-nostdin", "-v", "error", "-threads", "1", "-filter_threads", "1"]
    # Keep absolute stream PTS while seeking with preroll. Plain -ss/-t uses
    # the container start time and can lose a frame with AAC encoder delay.
    video_seek = max(0, start - 1)
    audio_seek = max(0, audio_start - 1)
    vc = base + [
        "-copyts",
        "-ss",
        str(video_seek),
        "-t",
        str(start + duration_sec - video_seek + 1),
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        f"select=gte(t\\,{start})*lt(t\\,{start+duration_sec}),setpts=N/(25*TB)",
        "-vsync",
        "0",
        "-pix_fmt",
        "rgb24",
        "-threads",
        "1",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    ac = base + [
        "-copyts",
        "-ss",
        str(audio_seek),
        "-t",
        str(audio_start + duration_sec - audio_seek + 1),
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-vn",
        "-af",
        f"atrim=start={audio_start}:end={audio_start+duration_sec},asetpts=N/SR/TB",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "f32le",
        "pipe:1",
    ]
    video = (
        np.frombuffer(subprocess.check_output(vc, timeout=120), dtype="uint8")
        .reshape(-1, h, w, 3)
        .copy()
    )
    audio = np.frombuffer(subprocess.check_output(ac, timeout=120), dtype="<f4").copy()
    if len(video) != int(duration_sec * 25) or len(audio) != int(duration_sec * 16000):
        raise ValueError(
            f"Incomplete window: {len(video)} frames / {len(audio)} audio samples; never substitute another example"
        )
    return video, audio


class RealSyncDataset:
    """Array-returning dataset compatible with PyTorch's dataset protocol."""

    def __init__(
        self, manifests, media_root, split="test", duration_sec=5, availability=None
    ):
        self.manifest = Manifest(manifests)
        self.samples = list(self.manifest.samples(split))
        self.media_root = media_root
        self.duration_sec = duration_sec
        if availability is not None:
            allowed = set(availability)
            unknown = allowed - {r["sample_id"] for r in self.samples}
            if unknown:
                raise ValueError("Availability contains IDs outside the selected split")
            self.samples = [r for r in self.samples if r["sample_id"] in allowed]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        row = self.samples[index]
        clip = self.manifest.clips[row["clip_id"]]
        path = safe_media_path(self.media_root, clip["relative_path"])
        video, audio = read_window(
            path, row["video_start_sec"], row["offset_sec"], self.duration_sec
        )
        return {
            "sample_id": row["sample_id"],
            "video": video,
            "audio": audio,
            "targets": {
                "offset_sec": row["effective_offset_sec"],
                "offset_target": row["offset_class"],
            },
            "metadata": row,
        }
