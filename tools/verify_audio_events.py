"""Verify frozen prediction coverage and lossless original-text recovery."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import read_jsonl
from tools.export_audio_events import historical_text, parse_prediction_text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifests', type=Path, default=Path(__file__).resolve().parents[1]/'manifests')
    args = p.parse_args()
    clips = {r['clip_id']: r for r in read_jsonl(args.manifests/'clips.jsonl.gz')}
    labels = list(read_jsonl(args.manifests/'annotations/audio_event_labels.jsonl'))
    label_map = {r['mid']:r['display_name'] for r in labels}
    if len(label_map) != len(labels):
        raise ValueError('Duplicate AudioSet MID')
    counts, seen, mids = Counter(), set(), set()
    by_split = {s:Counter() for s in ('train','val','test')}
    for row in read_jsonl(args.manifests/'annotations/audio_events.jsonl.gz'):
        key = row['clip_id']
        if key not in clips or key in seen:
            raise ValueError(f'Unknown or duplicate clip: {key}')
        seen.add(key)
        if row['status'] != 'observed' or not row['windows']:
            raise ValueError(f'This frozen release expects observed windows: {key}')
        if row['coordinate_system'] != 'decoded_pcm_sample_index' or row['sample_rate'] != 16000 or row['origin_in_prepared_pts_sec'] is not None:
            raise ValueError(f'Unexpected timing convention: {key}')
        text = historical_text(row['windows'])
        if parse_prediction_text(text, key) != row['windows']:
            raise ValueError(f'Lossy probability/window representation: {key}')
        if hashlib.sha256(text.encode()).hexdigest() != row['historical_text_sha256']:
            raise ValueError(f'Original text checksum differs: {key}')
        counts['observed'] += 1
        counts['windows'] += len(row['windows'])
        by_split[clips[key]['split']]['observed'] += 1
        by_split[clips[key]['split']]['windows'] += len(row['windows'])
        for window in row['windows']:
            counts['retained_predictions'] += len(window['labels'])
            counts['windows_without_retained_labels'] += not window['labels']
            for label in window['labels']:
                if label['mid'] not in label_map:
                    raise ValueError(f'Unknown class: {label["mid"]}')
                mids.add(label['mid'])
    if seen != clips.keys():
        raise ValueError('Prediction coverage differs from selected clip inventory')
    report = json.loads((args.manifests.parent/'validation/audio_event_inventory.json').read_text())
    if dict(counts) != report['counts'] or {s:dict(v) for s,v in by_split.items()} != report['by_split']:
        raise ValueError('Prediction statistics differ from inventory report')
    if len(mids) != report['retained_label_classes'] or len(label_map) != report['label_map_classes']:
        raise ValueError('Class coverage differs from inventory report')
    checkpoint = json.loads((args.manifests.parent/'validation/audio_event_checkpoint.json').read_text())
    if set(checkpoint['label_dict'].values()) != label_map.keys():
        raise ValueError('Checkpoint label vocabulary differs from released label map')
    print(f'Audio-event verification passed: {len(seen)} clips; {counts["windows"]} windows; every original text checksum exact')


if __name__ == '__main__':
    main()
