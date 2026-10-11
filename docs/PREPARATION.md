# Preparation

Obtain source videos independently using the IDs in `manifests/sources.jsonl`. A directory of current full videos cannot yet be converted into the exact historical collection: the original segment-cutting/timestamp rules are still being recovered. Do not approximate those rules from filenames and call the output an exact reconstruction.

## Existing historical segments

The recovered processing chain has two stages:

1. Re-encode raw segments: H.264, yuv420p, CRF 10, 25 fps; scale the shortest side to 256 and crop to even dimensions; AAC, 16 kHz, mono.
2. Inspect the first decoded frame timestamps for video and audio, take their maximum, then stream-copy crop using `-ss`, `-reset_timestamps 1`, and `-c copy`.

The stream-copy crop can discard a leading GOP and change stream start times. This is part of the historical processing; replacing it with a conventional precise trim changes the prepared data. The recovered crop step reproduced every packet payload and timestamp for three audited clips.

Inputs must be arranged as `<input>/<source_id>/<clip_id>.mkv`. Output must be a new directory separate from inputs and manifests. Existing files are never overwritten. Encoded intermediates are retained for audit.

```bash
# Starting from historical raw segments:
realsync prepare --manifests manifests --input /path/to/raw-segments \
  --output /path/to/new-prepared --input-kind raw-segments

# Starting from historical re-encoded segments; perform only the crop:
realsync prepare --manifests manifests --input /path/to/encoded-segments \
  --output /path/to/new-cropped --input-kind encoded-segments
```

Use repeated `--clip-id` arguments for a small verification run. Preparation is serial and limits encoding/decoding threads to two. It uses CPU processing, writes a provenance log, and keeps input files intact.

The old files identify older FFmpeg encoder/muxer versions. The newly bounded re-encoding path has not yet been proven byte-equivalent to the historical encoder. Reproducing the crop from an existing encoded segment and rebuilding the complete chain from a full source are different claims.

## Full source videos

The interface accepts `--input-kind full-sources`, with one `<source_id>.mkv`, `.mp4`, or `.webm` per source. **It currently stops before creating any output**, because the required source-origin values are unrecovered. Recovering the original cutting script or calibrating exact source origins is necessary before enabling that path. Software/environment pinning and end-to-end comparison must then be completed.

## Missing or changed sources

Keep the canonical manifests unchanged. Generate a separate availability report. For evaluations, declare the exact subset of sample IDs and the release tag/commit. Do not replace missing clips with neighboring examples, regenerate offsets, or rebuild splits around currently available videos.

Presence and format checks do not certify source equivalence. Checks of timestamp registration and decoded content are required before a changed rendition can be described as equivalent.
