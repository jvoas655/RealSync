# Reproducibility status

This repository releases the author-selected cleaned uniform-offset collection. It intentionally excludes older normal-offset and duplicate manifest generations. Existing server artifacts remain unchanged.

## Verified

- All 303,363 exported sample positions and stored offsets match historical inputs exactly.
- Compressed legacy JSON files decompress to the exact historical bytes.
- All 303,363 effective offset classes match the historical PyTorch float32 grid calculation.
- The 670 source-video IDs are disjoint across train, validation, and test.
- Synthetic reader tests prove repeated reads are identical, positive offsets select later audio, incomplete windows fail, gzip exports are deterministic, and output/input path guards work.
- The recovered stream-copy crop reproduces all packet payloads and timestamps for three checked clips, using existing historical re-encoded inputs. This does not establish full-chain equivalence from raw or full source videos.
- An independent metadata rebuild reproduces all 16 exported artifacts byte for byte, including the archived CSV files.
- All 11,039 selected prepared files are present and probe as H.264 / 25 fps / shortest side 256, with AAC / 16 kHz / mono audio. This is a header inventory, not exhaustive decoding of every file.
- One frozen 5-second sample rebuilt from a historical raw segment using FFmpeg 4.2.2 and eight encoder threads has identical decoded video and audio. A comparison over the complete clip does not match; matching that sample is not evidence of complete-clip equivalence. Modern FFmpeg 4.4.2 with two encoder threads also differs. Both comparisons are retained in `validation/`.
- The recovered face-track workspace contains byte-identical copies of all 11,039 selected historical track-output files, including recorded failures. Input lists identify encoded media for 10,368 selected clips; original scripts establish the native AVI-frame timing convention.
- Saved BEATs audio-event outputs cover all 11,039 selected clips, with 647,635 windows and 2,101,390 retained predictions. Every window grid, label MID, probability, and original text checksum was validated; conversion back to historical text is byte exact. Checkpoint/script hashes and the recovered 527-class model configuration are retained. No inference was rerun to replace original outputs.

Evidence is stored in `validation/`. The per-clip header inventory is in `manifests/reference_media.jsonl.gz` and must be distinguished from end-to-end content/timeline verification.

## Remaining work before a complete reconstruction release

1. Recover original full-source-to-segment cutting rules, or recover/calibrate exact per-clip source origins against unchanged full sources. Nominal filename boundaries are insufficient.
2. Verify raw-segment re-encoding and cropping end to end, with pinned tool/library builds and decoder alignment tests.
3. Verify timestamp registration of both face-sync AVI-frame coordinates and BEATs decoded-WAV coordinates to prepared-media PTS. The original annotation scripts and their input-media conventions have been recovered; do not silently equate decoded frame/sample indices with container timestamps.
4. Audit the effective legacy evaluation subsets and preprocessing, including short streaming windows, skip IDs, and read-failure substitutions; recover the paper's exact model/evaluation configurations as needed.

Until these are resolved, a metadata/tooling prerelease is reproducible at the manifest level and usable with existing prepared clips, but **not a complete reconstruction of the published dataset from full videos**. Source absence or re-encoding are additional external limits, not explanations for these unresolved internal provenance gaps.

## Preserved facts and differences

The paper reports 670 videos, 11,124 clips, and 927 hours. The cleaned collection selected for this release has 11,039 clips and 919.917 nominal hours. Recorded buffered raw durations sum to a larger value. These quantities are not interchangeable. No extra clips have been silently added or removed to reconcile them.

The author selected the cleaned uniform-offset set for this release. Section 3.1 of the paper describes truncated-normal evaluation sampling. The stored uniform draws are preserved; this release must be identified as the cleaned uniform-offset collection rather than silently presented as the paper's normal-offset protocol.

The canonical test set is the historical `sports_and_news_uniform.test.json` (16,529 samples / 85 sources); validation is historical `evaluation` (16,944 samples / 74 sources). The second-server Synchformer directory aliases historical `evaluation` as `valid`. An older StreamSync loader reverses these names, but the archived later baseline evaluation population belongs to historical `test`. The selected cleaned manifests are distinct and disjoint. A different server directory contains duplicate manifests; those files are not part of this release.

Saved face-sync annotations cover 10,957 selected clips, with 82 recorded errors. Their aggregate implementation accepts tracks satisfying `(abs(offset_frames) <= 5 and confidence >= 0.5) or (abs(offset_frames) <= 8 and confidence >= 5)`. This differs from the simplified threshold description in the supplement; preserved annotations are identified as historical outputs rather than claimed to have been regenerated from the supplement alone.

The recovered face-processing workspace records encoded inputs named `videos_at_25fps-encode_script`. Its runner probes the first decoded audio/video timestamps, stream-copy trims at their maximum if positive, converts to 25 fps AVI, then reports track frame indices divided by 25. This is evidence for its preprocessing convention; per-clip registration to prepared-media PTS is still a separate check.
