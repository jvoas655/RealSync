# Reproducibility status

This repository releases the author-selected cleaned uniform-offset collection. It intentionally excludes older normal-offset and duplicate manifest generations. Existing server artifacts remain unchanged.

## Verified

- All 303,363 exported sample positions and stored offsets match historical inputs exactly.
- Compressed legacy JSON files decompress to the exact historical bytes.
- All 303,363 effective offset classes match the historical PyTorch float32 grid calculation.
- The 670 source-video IDs are disjoint across train, validation, and test.
- Synthetic reader tests prove repeated reads are identical, positive offsets select later audio, incomplete windows fail, gzip exports are deterministic, and output/input path guards work.
- The recovered stream-copy crop reproduces all packet payloads and timestamps for three checked clips, using existing historical re-encoded inputs. This does not establish full-chain equivalence from raw or full source videos.

Evidence is stored in `validation/`. Reference-media format inventory is being built separately and must be distinguished from end-to-end content/timeline verification.

## Remaining work before a complete reconstruction release

1. Recover original full-source-to-segment cutting rules, or recover/calibrate exact per-clip source origins against unchanged full sources. Nominal filename boundaries are insufficient.
2. Verify raw-segment re-encoding and cropping end to end, with pinned tool/library builds and decoder alignment tests.
3. Recover saved BEATs audio-event annotations and their timing/model provenance. Do not fabricate or silently recompute purported original labels.
4. Verify timestamp registration of saved face-sync annotations to cropped media.
5. Audit the effective legacy evaluation subsets and preprocessing, including short streaming windows, skip IDs, and read-failure substitutions; recover the paper's exact model/evaluation configurations as needed.

Until these are resolved, a metadata/tooling prerelease is reproducible at the manifest level and usable with existing prepared clips, but **not a complete reconstruction of the published dataset from full videos**. Source absence or re-encoding are additional external limits, not explanations for these unresolved internal provenance gaps.

## Preserved facts and differences

The paper reports 670 videos, 11,124 clips, and 927 hours. The cleaned collection selected for this release has 11,039 clips and 919.917 nominal hours. Recorded buffered raw durations sum to a larger value. These quantities are not interchangeable. No extra clips have been silently added or removed to reconcile them.

Historical filenames `test` and `evaluation` map to validation and test respectively in the original StreamSync loader. The selected cleaned manifests are distinct and disjoint. A different server directory contains duplicate manifests; those files are not part of this release.

Saved face-sync annotations cover 10,957 selected clips, with 82 recorded errors. Their aggregate implementation accepts tracks satisfying `(abs(offset_frames) <= 5 and confidence >= 0.5) or (abs(offset_frames) <= 8 and confidence >= 5)`. This differs from the simplified threshold description in the supplement; preserved annotations are identified as historical outputs rather than claimed to have been regenerated from the supplement alone.
