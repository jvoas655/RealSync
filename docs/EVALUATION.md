# Evaluation

The cleaned uniform-offset metadata is frozen. This release includes a strict direct-timeline reader and a coverage-checking metric utility. It does not yet certify reproduction of the paper's model scores.

## Direct-timeline reference view

`RealSyncDataset` uses the frozen `video_start_sec`, effective two-decimal audio offset, and explicit duration. FFmpeg stream timestamps are preserved during seeking and trimming; incomplete windows raise errors. There is no hidden replacement, padding, resampling of offsets, or random evaluation augmentation.

The historical StreamSync loader used additional seek buffers and fixed slicing, filtered skip IDs, shuffled/capped some evaluation sets, and could recursively substitute a previous sample after failure. Those details matter when reproducing its scores. The original JSON manifests are retained so historical experiments can be investigated; the new reader's outputs should not be presented as identical to that loader without comparison.

## Streaming protocol

The main paper reports 18 windows with a 2-second hop. With a 5-second window, the visible sequence spans 39 seconds (`5 + 17*2`). Keep the injected offset fixed throughout a sequence and reset model state between independent samples. Report which window length, hop, number of windows, and prediction-selection rule you use.

Some frozen sample starts are valid for a 5-second snapshot but lack enough remaining audio/video for a 39-second sequence. Those samples must be explicitly excluded for that protocol, with an evaluated-ID list. Never silently substitute them. The legacy loader's complete effective subset and failure behavior remain to be audited before claiming the paper's exact evaluation population.

## Metric input

Provide JSONL with one row per evaluated sample:

```json
{"sample_id":"<frozen sample ID>","logits":["21 finite numeric values"]}
```

For streaming models, supply logits from the declared final iteration. For snapshot baselines, explicitly identify any selection across windows; a ground-truth-assisted best-window rule differs from deployable inference. The utility does not make that choice for you.

```bash
realsync evaluate --manifests manifests --split test --predictions predictions.jsonl

# An explicit partial-coverage evaluation:
realsync evaluate --manifests manifests --split test --predictions predictions.jsonl \
  --subset evaluated_ids.json
```

`evaluated_ids.json` is a JSON list of the exact evaluated sample IDs. Duplicate, missing, unexpected, or non-finite predictions fail validation. Metrics include exact accuracy, ±1-class tolerance accuracy, macro average precision, and macro one-vs-rest ROC AUC. Classes without both positive and negative examples are explicitly listed and excluded from ranking-metric averages; such partial-coverage numbers are not directly comparable to the full benchmark.

Always report release tag/commit, source availability, prepared-media provenance, reader/protocol, and evaluated sample count. Preserve the evaluated-ID list with results.
