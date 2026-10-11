"""Score logits tied to frozen sample IDs; never silently drop missing rows."""
import json
from pathlib import Path
from .io import read_jsonl


def evaluate(manifest, predictions, split="test", expected_ids=None):
    import numpy as np
    from sklearn.metrics import average_precision_score, roc_auc_score

    samples = {r["sample_id"]: r for r in manifest.samples(split)}
    expected = set(samples) if expected_ids is None else set(expected_ids)
    if not expected <= samples.keys():
        raise ValueError("Subset includes IDs outside selected split")
    if not expected:
        raise ValueError("Cannot evaluate an empty subset")
    predictions = list(read_jsonl(predictions))
    lookup = {r["sample_id"]: r for r in predictions}
    if len(lookup) != len(predictions):
        raise ValueError("Duplicate prediction IDs")
    if set(lookup) != expected:
        raise ValueError(
            f"Prediction coverage mismatch: {len(expected-set(lookup))} missing, {len(set(lookup)-expected)} unexpected. Provide the explicit evaluated subset; do not silently drop rows."
        )
    ordered = sorted(expected)
    logits = np.array([lookup[k]["logits"] for k in ordered], dtype=np.float64)
    if logits.shape != (len(ordered), 21) or not np.isfinite(logits).all():
        raise ValueError("Each prediction needs 21 finite logits")
    labels = np.array([samples[k]["offset_class"] for k in ordered])
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    probs = exp / exp.sum(axis=1, keepdims=True)
    pred = probs.argmax(axis=1)
    truth = np.eye(21, dtype=np.int64)[labels]
    auc = []
    aps = []
    absent = []
    for i in range(21):
        if truth[:, i].min() == truth[:, i].max():
            absent.append(i)
            continue
        aps.append(float(average_precision_score(truth[:, i], probs[:, i])))
        auc.append(float(roc_auc_score(truth[:, i], probs[:, i])))
    return {
        "split": split,
        "samples": len(ordered),
        "canonical_samples": len(samples),
        "accuracy": float(np.mean(pred == labels)),
        "accuracy_tolerance_1": float(np.mean(np.abs(pred - labels) <= 1)),
        "mAP_present_classes": float(np.mean(aps)) if aps else None,
        "macro_roc_auc_present_classes": float(np.mean(auc)) if auc else None,
        "classes_excluded_from_ranking_metrics": absent,
        "evaluation_protocol": "one supplied logit vector per frozen ID; full-stream final-iteration vs snapshot selection must be declared separately",
    }
