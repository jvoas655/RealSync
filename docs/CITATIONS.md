# Citations and contributions

## Citing RealSync

When using RealSync, cite its primary publication, **Temporally Streaming Audio-Visual Synchronization for Real-World Videos** (Voas et al., WACV 2025), which introduces RealSync and StreamSync. Link to the [paper](https://openaccess.thecvf.com/content/WACV2025/papers/Voas_Temporally_Streaming_Audio-Visual_Synchronization_for_Real-World_Videos_WACV_2025_paper.pdf) and identify this repository's release tag/commit and the evaluated sample IDs. `CITATION.cff` makes that paper the preferred citation in GitHub's citation interface.

```bibtex
@InProceedings{Voas_2025_WACV,
  author = {Voas, Jordan and Tseng, Wei-Cheng and Berry, Layne and Hu, Xixi and Peng, Puyuan and Stuedemann, James and Harwath, David},
  title = {Temporally Streaming Audio-Visual Synchronization for Real-World Videos},
  booktitle = {Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)},
  month = {February},
  year = {2025},
  pages = {5009--5017},
  url = {https://openaccess.thecvf.com/content/WACV2025/papers/Voas_Temporally_Streaming_Audio-Visual_Synchronization_for_Real-World_Videos_WACV_2025_paper.pdf}
}
```

Suggested release identification: “We use RealSync v0.1.0, the cleaned uniform-offset metadata release, with [N] evaluated samples from [split]; our prepared-media provenance and availability subset are reported separately.” The released clean uniform collection differs from the paper's headline clip count and described normal-offset sampling; see [dataset guide](DATASET_GUIDE.md).

## Source material and annotation methods

| Contribution | Role in this release | Reference/attribution |
|---|---|---|
| Original YouTube publishers | Source footage in nine preserved sports/news collection groups | Attribute original videos/publishers through the URLs/IDs in `sources.jsonl`; source-media rights remain with their owners |
| S3FD | Face detection in the recovered talking-head pipeline | [Zhang et al., ICCV 2017](https://openaccess.thecvf.com/content_iccv_2017/html/Zhang_S3FD_Single_Shot_ICCV_2017_paper.html) |
| SyncNet | Audio–lip offset/confidence estimates underlying saved face-track annotations | [Chung and Zisserman, ACCV workshop 2016](https://robots.ox.ac.uk/~vgg/publications/2016/Chung16a/) |
| BEATs | Model used to generate the released audio-event predictions | [Chen et al., ICML 2023](https://proceedings.mlr.press/v202/chen23ag.html) |
| AudioSet | Event-label vocabulary and training context for the BEATs classifier | [Gemmeke et al., ICASSP 2017](https://research.google/pubs/audio-set-an-ontology-and-human-labeled-dataset-for-audio-events/), [ontology](https://research.google.com/audioset/ontology/index.html) |
| SparseSync | Historical synchronization model/code lineage and offset-transform conventions | [Iashin et al., BMVC 2022](https://arxiv.org/abs/2210.07055), [original code](https://github.com/v-iashin/SparseSync) |

Cite the relevant annotation methods when using or analyzing those annotation layers, and SparseSync when building on the inherited model implementation. AudioSet contributes a vocabulary/model background here; this release does not distribute AudioSet clips, or assert that RealSync source videos are an AudioSet subset. Saved predictions are automatic annotations, not original AudioSet human labels. Other third-party corpora and pretrained weights are not bundled.

Code is MIT licensed and metadata/annotations use CC BY 4.0; see [code license](../LICENSE) and [metadata license](../DATA_LICENSE.md). Those licenses do not grant source-video redistribution rights.

## Subsequent work using RealSync comparisons

[Toward Robust Audio-Visual Synchronization Detection in Egocentric Video with Sparse Synchronization Events](https://bmvc2025.bmva.org/proceedings/903/) (Voas et al., BMVC 2025) presents AS-Synchformer and compares egocentric synchronization with RealSync. Its Table 1 carries RealSync results from prior work; this release does not claim to reproduce that paper's Ego4D experiments or redistribute its egocentric data.

```bibtex
@inproceedings{Voas_2025_BMVC,
  author = {Jordan Voas and Wei-Cheng Tseng and Benoit Vallade and Alex Mackin and David Higham and David Harwath},
  title = {Toward Robust Audio-Visual Synchronization Detection in Egocentric Video with Sparse Synchronization Events},
  booktitle = {British Machine Vision Conference (BMVC)},
  publisher = {BMVA},
  year = {2025},
  url = {https://bmvc2025.bmva.org/proceedings/903/}
}
```

Cite this subsequent paper when discussing AS-Synchformer or those transfer comparisons. The WACV paper remains the primary RealSync citation. Bibliography entries for both papers and the contributing methods are collected in [CITATIONS.bib](CITATIONS.bib).
