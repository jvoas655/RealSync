# Frozen manifest schema

All times are seconds. Sample floats are the exact values parsed from historical JSON, not regenerated draws. Compressed JSONL files use gzip with a fixed header timestamp. Records are sorted by stable ID; original ordering and bytes are retained separately in `legacy/`.

## Files

| File | Contents |
|---|---|
| `sources.jsonl` | Source ID, URL, category, split, and selected historical acquisition/rendition metadata. No expiring URLs or HTTP headers. |
| `clips.jsonl.gz` | Stable clip ID, relative filename, nominal source boundaries, historical durations, and source-origin recovery status. |
| `train.jsonl.gz`, `val.jsonl.gz`, `test.jsonl.gz` | Frozen sample positions and offsets with effective float32 class labels. |
| `annotations/*.jsonl.gz` | Saved intervals in historical annotation-clip coordinates. |
| `annotations/errors.json` | Clips with recorded annotation failures. |
| `legacy/*.json.gz`, `legacy/*.csv.gz` | Exact historical sample JSON/CSV bytes and ordering, compressed deterministically. |
| `provenance.json` | Hashes of the historical artifacts and the split-name mapping. |
| `summary.json` | Counts, labels, annotation coverage, and nominal duration. |
| `reference_media.jsonl.gz` | Observed prepared-file sizes, stream formats, and container/stream timing headers. No media payloads. |

Historical names map as follows: `train` → train, `test` → validation, `evaluation` → test. This mapping follows the historical StreamSync dataset loader. The cleaned source IDs are disjoint across all three splits.

## Sample fields

- `sample_id`: original stable sample key; treat as opaque rather than deriving fields from underscores.
- `source_id`, `clip_id`, `split`: explicit identity and split references.
- `video_start_sec`: stored `v_start_i_sec`, a location within the prepared clip's timeline.
- `offset_sec`: original stored continuous offset, preserved without rounding.
- `effective_offset_sec`: Python `round(offset_sec, 2)`, as used in the historical fixed-offset transform.
- `offset_class`: nearest class index, using historical float32 grid arithmetic; 0 corresponds to −2 seconds, 10 to zero, 20 to +2 seconds.
- `offset_label_sec`: the float32 class-center value.

The direct-timeline reference view extracts video at `video_start_sec` and audio at `video_start_sec + effective_offset_sec`. For positive offsets the audio contains an event from a later source time and therefore leads the video. An injected offset is not an assertion that the original source itself is perfectly synchronized.

## Source coordinates

`nominal_source_start_sec` and `nominal_source_end_sec` come from historical clip filenames. **They do not establish the exact source origin of the stored clip.** Raw segments have extra context and can contain leading undecodable video frames. `source_origin_sec` is currently null, and full-source preparation refuses to guess it.

Historical track lengths are decoded lengths used by the cleaning scripts, not necessarily container duration or timestamp endpoints. Saved face-sync annotation intervals have their own historical clip coordinate system; exact registration to the cropped clips remains to be verified. A missing annotation record, an error record, and an observed empty interval list are distinct states.
