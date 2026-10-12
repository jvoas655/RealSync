# Reconstruction walkthrough

This walkthrough distinguishes **reproducing released metadata**, **reading historical prepared clips**, and **rebuilding media**. Exact reconstruction of the historical collection from full source videos remains incomplete because original cutting rules/source origins are unrecovered. Current YouTube downloads plus nominal filename boundaries do not certify the frozen targets.

## 1. Install and verify the tagged release

Use Python 3.11 with FFmpeg/ffprobe. The reference reader was checked with FFmpeg 4.4.2 on Ubuntu 22.04; the historical encoder is a separate toolchain.

```bash
git clone https://github.com/jvoas655/RealSync.git
cd RealSync
git checkout v0.1.0
python -m pip install -e '.[load,eval]'
sha256sum -c SHA256SUMS
realsync audit --manifests manifests
python tools/verify_audio_events.py
mkdir -p work
ffmpeg -version > work/ffmpeg-version.txt
```

The repository already contains the metadata. Alternatively, download `realsync-metadata-v0.1.0.tar.gz` and its checksum from the [release](https://github.com/jvoas655/RealSync/releases/tag/v0.1.0):

```bash
sha256sum -c realsync-metadata-v0.1.0.tar.gz.sha256
mkdir extracted-metadata
tar -xzf realsync-metadata-v0.1.0.tar.gz -C extracted-metadata
```

The archive contains `manifests/` and `validation/`; use the tagged code checkout for the reader/documentation. Stored sample starts, offsets, splits, and annotation identities are frozen. Never redraw offsets or remake splits to fit source availability.

## 2. Identify your media inputs

| Input | What works now | Equivalence status |
|---|---|---|
| No media | Inspect/audit manifests and saved annotations | Metadata operations fully supported |
| Historical prepared clips | Validate and read frozen sample windows | Supported by the strict reference reader |
| Historical encoded segments | Run the recovered stream-copy crop | Every compressed packet/timestamp matched in three audited examples |
| Historical raw segments | Run recovered encoding plus cropping | Formats supported; exact complete-clip historical equivalence still unverified |
| Independently obtained full videos | Record source identity/rendition and availability | Exact cutting unresolved; `full-sources` stops before creating outputs |

Identify original URLs/IDs and historical rendition metadata in `manifests/sources.jsonl`. Researchers obtain videos from their original publishers. Record removed, edited, or changed-rendition sources explicitly. Downloader success or matching codec/dimensions does not establish unchanged content/timing.

The intended full-source layout is one `<source_id>.mkv`, `.mp4`, or `.webm` per source. The current `source_origin_sec` values are null: **do not substitute nominal filename times**. Historical segments include context and can contain leading undecodable frames. Recovering/calibrating those boundaries and matching renditions is necessary before exact full-source reconstruction is enabled.

## 3. Arrange and validate prepared clips

```text
prepared-clips/
  EYX_ijEC-ps/
    EYX_ijEC-ps_900_1200.mkv
  <source_id>/
    <clip_id>.mkv
```

Use each clip's authoritative `relative_path` in `clips.jsonl.gz`. Output/report paths must be new and separate from media inputs.

```bash
realsync validate --manifests manifests --media /path/to/prepared-clips \
  --report work/availability.json

# Reads every present file for format inspection and full file hashing:
realsync validate --manifests manifests --media /path/to/prepared-clips \
  --report work/availability-deep.json --deep --workers 2
```

Presence reports use `present_unverified`; deep reports inspect format and hash files. `format_ok` does not certify original content/timing or valid decoding at every window. The released reference inventory contains headers and sizes, not complete historical per-file content hashes. Strict reads can still reject incomplete windows.

## 4. Read the same frozen sample twice

```python
import json
import numpy as np
from realsync.loader import RealSyncDataset

with open("work/availability.json") as f:
    available = json.load(f)["available_ids"]["test"]
dataset = RealSyncDataset(
    "manifests", "/path/to/prepared-clips", split="test",
    duration_sec=5, availability=available,
)
first = dataset[0]  # Raises if the selected window is incomplete.
repeat = dataset[0]
assert np.array_equal(first["video"], repeat["video"])
assert np.array_equal(first["audio"], repeat["audio"])
print(first["sample_id"], first["targets"])
# video: uint8 [125,H,W,3]; audio: float32 [80000] at 16 kHz
```

Video uses the stored start; audio uses that start plus the effective two-decimal offset. Pin source identity, prepared-media bytes, decoder versions, and reader behavior for array reproduction. The reader preserves timestamps and fails explicitly on incomplete reads. Its behavior differs from the historical model loader's additional seek/slice logic; see [evaluation](EVALUATION.md).

An availability list is a presence/format subset, not a complete-window guarantee. For longer reads, save the exact IDs meeting the chosen protocol and log rejected windows. The WACV main protocol's 18 five-second windows with two-second hop span 39 seconds. Keep the same frozen offset across the sequence and reset state between independent samples.

## 5. Rebuild from historical segments

Use the same `<source_id>/<clip_id>.mkv` input layout. Start with one selected clip and new output directories:

```bash
realsync prepare --manifests manifests --input /path/to/raw-segments \
  --output work/raw-rebuild --input-kind raw-segments \
  --clip-id EYX_ijEC-ps_900_1200

realsync prepare --manifests manifests --input /path/to/encoded-segments \
  --output work/encoded-crop-rebuild --input-kind encoded-segments \
  --clip-id EYX_ijEC-ps_900_1200
```

Repeat `--clip-id` for multiple clips; omit it for the entire inventory. Preparation is serial, preserves input files, and keeps encoded intermediates. `preparation.json` records commands, tool version, input/output hashes, crop timestamp, and clip status. Missing inputs stay explicit.

The chain encodes H.264 / yuv420p / CRF 10 / 25 fps / shortest side 256 / even dimensions and AAC / mono / 16 kHz. It then probes the first decoded A/V timestamps, takes their maximum, and stream-copy crops there. A leading GOP can be discarded; substituting a precise trim changes historical behavior. [Technical preparation details](PREPARATION.md) explain the command sequence and toolchain evidence.

`--ffmpeg`, `--ffprobe`, and `--encoder-threads` select explicit binaries/thread counts. Available FFmpeg 4.2.2 with eight encoder threads matched one five-second RGB/PCM sample exactly but differed over the complete clip. The modern default also differed. Neither eight threads nor a matching short sample establishes complete historical equivalence.

If reference prepared media are available, compare complete decoded content:

```bash
python tools/verify_reader.py --help
python tools/verify_decoded_clip.py --manifests manifests \
  --reference /path/to/prepared-clips --rebuilt work/raw-rebuild \
  --clip-id EYX_ijEC-ps_900_1200 --report work/full-clip-comparison.json
```

The complete-clip checker streams RGB/PCM hashes without buffering a whole clip. Preserve mismatches alongside successful checks.

## 6. Use saved annotations and report availability

No model inference is needed to recover the released annotation values. `tools/verify_audio_events.py` validates all retained predictions and reconstructs every original prediction text checksum. Join annotation records by `clip_id` and event names by AudioSet MID. Keep face AVI-frame coordinates and BEATs decoded-WAV coordinates separate from prepared-media timestamps until registration is verified. [Dataset guide](DATASET_GUIDE.md) and [schema](SCHEMA.md) describe those layers.

Keep canonical manifests unchanged. Report the exact evaluated IDs, source availability, media hashes/provenance, release tag/commit, decoder versions, window/protocol, and rejected reads. Never replace missing clips or rebuild splits around current downloads. Follow [evaluation](EVALUATION.md) for coverage and scoring, and [citations](CITATIONS.md) for attribution.
