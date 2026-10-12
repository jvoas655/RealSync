# RealSync

Metadata and reconstruction tooling for **Temporally Streaming Audio-Visual Synchronization for Real-World Videos**, WACV 2025.

[Paper](https://openaccess.thecvf.com/content/WACV2025/papers/Voas_Temporally_Streaming_Audio-Visual_Synchronization_for_Real-World_Videos_WACV_2025_paper.pdf) · [Supplement](https://openaccess.thecvf.com/content/WACV2025/supplemental/Voas_Temporally_Streaming_Audio-Visual_WACV_2025_supplemental.pdf) · [StreamSync](https://github.com/jvoas655/StreamSync)

[Dataset guide](docs/DATASET_GUIDE.md) · [Reconstruction walkthrough](docs/RECONSTRUCTION.md) · [Citations and contributions](docs/CITATIONS.md) · [Subsequent BMVC 2025 paper](https://bmvc2025.bmva.org/proceedings/903/)

**Release v0.1.0: verified manifests, annotations, and tools.** The cleaned uniform-offset manifests and saved BEATs audio-event outputs are frozen and verified. Complete reconstruction from full source videos remains pending: original cutting rules, exact historical re-encoding, and annotation registration to prepared-media timestamps still need verification. See [reproducibility status](docs/REPRODUCIBILITY.md).

[Download v0.1.0](https://github.com/jvoas655/RealSync/releases/tag/v0.1.0) includes a metadata archive and SHA-256 checksum. The tagged repository also contains the reader, preparation tools, documentation, and validation evidence.

No original videos, audio, thumbnails, face crops, or media embeddings are distributed. Researchers obtain source videos themselves; the source URLs and IDs are listed in `manifests/sources.jsonl`.

## What is included

The author-selected **cleaned uniform-offset collection** contains 670 source videos and 11,039 nominal five-minute clips from nine sports/news categories. The frozen sample counts are:

| Split | Source videos | Samples |
|---|---:|---:|
| Train | 511 | 269,890 |
| Validation | 74 | 16,944 |
| Test | 85 | 16,529 |

No source video is shared between splits. Sample positions and continuous offsets are preserved exactly. Effective offsets are rounded to two decimals, then classified on the historical 21-class float32 grid between −2 and +2 seconds. Positive offsets extract audio from a later source time: the audible event leads its visual counterpart.

Saved talking-head/voice-over intervals cover 10,957 clips; 82 clips have recorded annotation errors. Empty intervals mean no detected intervals, not missing annotation. Annotation timeline registration is still under review. Older normal-offset and duplicate server manifests are excluded.

Saved BEATs audio-event predictions cover all 11,039 selected clips: 647,635 overlapping 10-second windows and 2,101,390 retained label probabilities. These preserve the original top-10 predictions retained at probability ≥ 0.1, rounded to four decimals. They are model predictions, not human labels or complete probability vectors. See [annotation conventions](docs/SCHEMA.md#audio-event-annotations).

The paper reports 11,124 clips / 927 hours. This release preserves the explicitly selected cleaned collection rather than silently expanding it to match those headline numbers. Its nominal clip duration sums to 919.917 hours; buffered file duration is a different quantity.

## Quick start

Use Python 3.11. The reference run used FFmpeg 4.4.2 on Ubuntu 22.04; tool versions and checks are in `validation/`.

```bash
git clone https://github.com/jvoas655/RealSync.git
cd RealSync
python -m pip install -e '.[load,eval]'
realsync audit --manifests manifests
```

For existing prepared clips, arranged as `<media>/<source_id>/<clip_id>.mkv`:

```bash
realsync validate --manifests manifests --media /path/to/prepared-clips \
  --report /path/to/new-availability.json
```

Add `--deep` to probe formats and compute media hashes. Presence checks alone do not certify valid decoding or equivalent source timelines. No input is modified; preparation requires a separate new output directory.

```python
from realsync.loader import RealSyncDataset

dataset = RealSyncDataset("manifests", "/path/to/prepared-clips", split="test")
item = dataset[0]  # video: uint8 [T,H,W,3], audio: float32 [samples]
print(item["sample_id"], item["targets"])
```

The reference reader uses manifest timestamps directly and fails explicitly on incomplete windows. It does not silently substitute another sample. Its timing behavior is distinct from historical StreamSync loader seeking; see [evaluation](docs/EVALUATION.md) before comparing results to the paper.

## Reconstruction and evaluation

- [Reconstruction walkthrough](docs/RECONSTRUCTION.md)
- [Technical preparation details and current limits](docs/PREPARATION.md)
- [Manifest schema and coordinate conventions](docs/SCHEMA.md)
- [Evaluation and reporting available subsets](docs/EVALUATION.md)
- [Evidence, provenance, and remaining reconstruction work](docs/REPRODUCIBILITY.md)

The complete original JSON manifests are also preserved as compressed files in `manifests/legacy/`. A tagged GitHub release freezes the code, manifests, and checksums together. Always report the tag/commit and evaluated sample IDs; source availability can change.

## Citation and licenses

Please cite the WACV paper and identify the RealSync release tag used. `CITATION.cff` provides the paper citation. Code is MIT licensed; released metadata/annotations use CC BY 4.0 as described in [DATA_LICENSE.md](DATA_LICENSE.md). Neither license grants rights to source videos.

The [citation guide](docs/CITATIONS.md) explains source-publisher attribution, S3FD/SyncNet face annotations, BEATs/AudioSet event annotations, and the SparseSync model/code lineage. It also includes the [BMVC 2025 AS-Synchformer paper](https://bmvc2025.bmva.org/proceedings/903/), which uses RealSync in its transfer-performance comparisons. Full BibTeX entries are available in [CITATIONS.bib](docs/CITATIONS.bib).

```bibtex
@InProceedings{Voas_2025_WACV,
  author = {Voas, Jordan and Tseng, Wei-Cheng and Berry, Layne and Hu, Xixi and Peng, Puyuan and Stuedemann, James and Harwath, David},
  title = {Temporally Streaming Audio-Visual Synchronization for Real-World Videos},
  booktitle = {Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)},
  month = {February},
  year = {2025},
  pages = {5009--5017}
}
```
