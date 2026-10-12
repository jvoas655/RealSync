# Dataset guide

RealSync measures audio–visual synchronization in long broadcast-style YouTube videos. The primary publication is the [WACV 2025 StreamSync paper](https://openaccess.thecvf.com/content/WACV2025/papers/Voas_Temporally_Streaming_Audio-Visual_Synchronization_for_Real-World_Videos_WACV_2025_paper.pdf). This release freezes the author-selected **cleaned uniform-offset collection**. See [citations and provenance](CITATIONS.md) for the paper and annotation-method references.

## Sources, clips, and samples

These are three different units:

| Unit | Meaning | Count | Where to find it |
|---|---|---:|---|
| Source | A full original YouTube video, identified by its 11-character ID | 670 | `manifests/sources.jsonl` |
| Clip | A historically prepared segment with nominal five-minute source boundaries | 11,039 | `manifests/clips.jsonl.gz` |
| Sample | A stored video start and audio offset within a prepared clip | 303,363 | `manifests/{train,val,test}.jsonl.gz` |

A sample is a rendering instruction, not a separately distributed media file. Multiple samples refer to the same clip. The reference reader defaults to a five-second window; longer streaming sequences require sufficient remaining media and an explicitly declared protocol.

Prepared clips use H.264 video at 25 fps, shortest image side 256 pixels with even dimensions, and AAC mono audio at 16 kHz. Clip durations need not be exactly 300 seconds: historical buffering, decoded stream lengths, and stream-copy cropping affect boundaries. Nominal filenames do not establish exact positions in a newly obtained full video.

## Splits and source groups

| Split | Full source videos | Clips | Frozen samples |
|---|---:|---:|---:|
| Train | 511 | 9,808 | 269,890 |
| Validation (`val`) | 74 | 618 | 16,944 |
| Test | 85 | 613 | 16,529 |

Splits are separated by full source ID, so one source cannot contribute clips to two splits. One test clip has no frozen sample windows but remains part of the clip/annotation inventory. Historical filenames use `evaluation` for canonical validation and `test` for canonical test. Use the explicit release mapping rather than the reversed aliases in some old model code.

The source-group names are preserved exactly:

| Category | Source videos |
|---|---:|
| `ABCNews` | 40 |
| `CBSNews` | 33 |
| `CNN` | 93 |
| `NBCNews` | 174 |
| `golfshome` | 141 |
| `NFL` | 51 |
| `NHL` | 59 |
| `mlb` | 30 |
| `WTA` | 49 |

These are collection/channel groups, not per-window sound-event ground truth. The release contains 919.917 nominal clip hours. The WACV paper's headline collection is larger (11,124 clips / 927 hours), and it describes a truncated-normal offset protocol. This release contains the selected cleaned subset and frozen uniform draws; identify that distinction when reporting results.

## What the offset means

For a sample with video start `t`, effective offset `d`, and window length `L`, the direct-timeline reader extracts video over `[t, t+L)` and audio over `[t+d, t+d+L)`. Positive `d` therefore selects later source audio, making the audible event lead its visual counterpart. Negative `d` makes it lag. The stored draw is preserved in `offset_sec`; `effective_offset_sec` is its historical two-decimal rounding.

`offset_class` is the nearest point on the historical float32 grid of 21 classes from −2 to +2 seconds in 0.2-second increments. Class 10 is zero. The injected offset is the target; it does not certify that the original broadcast had zero intrinsic synchronization error.

For example, frozen test sample `-Ma9vEFqnuk_0_300_100_0` has video start 100 seconds, stored offset −1.6229135637953531 seconds, effective offset −1.62 seconds, and class 2. A five-second read takes video at `[100,105)` and audio at `[98.38,103.38)` in the prepared timeline. Treat sample IDs as opaque; use explicit record fields for joins.

## Annotation layers

| Layer | What it contains | Coverage | Interpretation |
|---|---|---|---|
| Talking head | Saved intervals accepted by the historical face-sync aggregation | 10,957 clips | Model-derived face/lip synchronization evidence |
| Voice-over | Saved face-track intervals rejected by that aggregation | 10,957 clips | Historical heuristic output; not comprehensive human voice-over labels |
| Annotation errors | Clip IDs with recorded face-pipeline failures | 82 clips | Failure state, distinct from observed empty intervals |
| Audio events | Saved BEATs predictions on overlapping ten-second windows | All 11,039 clips; 647,635 windows | Top-10 AudioSet classes retained at probability ≥ 0.1, rounded to four decimals |

Face intervals use historical annotation coordinates derived from the processing AVI's frame indices divided by 25. BEATs window coordinates start at the first extracted WAV sample, with a five-second hop. Their registration to prepared-media presentation timestamps remains unverified. Preserve these native coordinates; do not silently overlay them on a video timestamp axis.

The audio-event file retains 2,101,390 probabilities. Missing classes have unknown probabilities, not zero probabilities. The 527-class label map supplies readable names for AudioSet MIDs; 521 classes occur in retained predictions. The saved statistics script used a separate 0.5 reporting threshold, while this release preserves predictions down to 0.1. Empty predicted-label lists do not mean missing windows.

## File map

| Path | Purpose |
|---|---|
| `manifests/sources.jsonl` | Source URLs/IDs, category, split, selected historical rendition metadata |
| `manifests/clips.jsonl.gz` | Clip identity, expected relative path, nominal boundaries, duration metadata, source-origin status |
| `manifests/train.jsonl.gz`, `val.jsonl.gz`, `test.jsonl.gz` | Frozen sample instructions and offset targets |
| `manifests/annotations/talking_head.jsonl.gz`, `voice_over.jsonl.gz` | Per-clip native-coordinate intervals and status |
| `manifests/annotations/errors.json` | Recorded face-annotation failure IDs |
| `manifests/annotations/audio_events.jsonl.gz` | Per-clip windows and retained MIDs/probabilities; original text checksums |
| `manifests/annotations/audio_event_labels.jsonl` | AudioSet MID-to-name map |
| `manifests/annotations/audio_event_provenance.json` | BEATs checkpoint/script hashes and extraction/windowing conventions |
| `manifests/legacy/` | Exact historical clean uniform-offset JSON and CSV bytes, gzip compressed |
| `manifests/reference_media.jsonl.gz` | Historical prepared-file headers and sizes; no media payloads or complete per-file content hashes |
| `manifests/summary.json`, `provenance.json` | Base collection counts, input fingerprints, historical split mapping |
| `validation/` | Rebuild, annotation, media-header, and decoding comparison evidence |
| `realsync/` | Strict reader, manifest handling, preparation, and evaluation code |
| `SHA256SUMS` | Checksums of the tagged repository's released files |

Read gzip JSONL without unpacking it:

```python
from realsync.io import read_jsonl

first = next(read_jsonl("manifests/test.jsonl.gz"))
print(first["sample_id"], first["clip_id"], first["effective_offset_sec"])
```

This release includes no source media, thumbnails, face crops, embeddings, or pretrained model-weight binaries. Follow [preparation](PREPARATION.md) to see which inputs can be used now, [schema](SCHEMA.md) for exact fields, and [evaluation](EVALUATION.md) for protocol/coverage rules.
