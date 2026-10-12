"""Freeze recovered BEATs text predictions without inference or media writes.

The historical script records top-10 labels with probability >= 0.1, rounded
to four decimal places. These are partial predictions, not full class logits.
The output directory must be new and separate from every input directory.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realsync.io import dump_json, new_output_root, read_jsonl, sha256, write_jsonl

WINDOW = re.compile(r'^\[([0-9.]+), ([0-9.]+)\](.*)$')


def parse_prediction_text(text, name='predictions'):
    windows = []
    for number, line in enumerate(text.splitlines(), 1):
        match = WINDOW.fullmatch(line)
        if not match:
            raise ValueError(f'{name}:{number}: invalid window record')
        start, end = float(match[1]), float(match[2])
        if start != (number - 1) * 5.0 or end != start + 10.0:
            raise ValueError(f'{name}:{number}: unexpected window grid')
        labels = []
        for token in match[3].split():
            label, probability = token.rsplit(',', 1)
            probability = float(probability)
            if not re.fullmatch(r'/[a-z]/[A-Za-z0-9_]+', label) or not math.isfinite(probability) or not 0.1 <= probability <= 1:
                raise ValueError(f'{name}:{number}: invalid prediction')
            labels.append({'mid': label, 'probability': probability})
        if len(labels) > 10 or len({r['mid'] for r in labels}) != len(labels):
            raise ValueError(f'{name}:{number}: invalid top-10 labels')
        if any(a['probability'] < b['probability'] for a, b in zip(labels, labels[1:])):
            raise ValueError(f'{name}:{number}: unsorted probabilities')
        windows.append({'start_sec': start, 'end_sec': end, 'labels': labels})
    return windows


def parse_predictions(path):
    return parse_prediction_text(path.read_text(), path.name)


def historical_text(windows):
    return ''.join(f"[{w['start_sec']:.1f}, {w['end_sec']:.1f}]" +
                   ''.join(f" {p['mid']},{p['probability']:.4f}" for p in w['labels']) + '\n'
                   for w in windows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifests', required=True, type=Path)
    p.add_argument('--beats-workspace', required=True, type=Path)
    p.add_argument('--checkpoint', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    output = new_output_root(args.output, [args.manifests, args.beats_workspace, args.checkpoint])
    clips = list(read_jsonl(args.manifests / 'clips.jsonl.gz'))
    label_path = args.beats_workspace / 'class_labels_indices.csv'
    with label_path.open(newline='') as f:
        label_map = {r['mid']: r['display_name'] for r in csv.DictReader(f)}
    rows, counts, labels, lengths = [], Counter(), Counter(), Counter()
    missing, no_windows = [], []
    by_split = {split: Counter() for split in ('train', 'val', 'test')}
    input_bytes = 0
    for clip in clips:
        path = args.beats_workspace / 'output' / clip['source_id'] / (clip['clip_id'] + '.txt')
        row = {'clip_id': clip['clip_id'], 'coordinate_system': 'decoded_pcm_sample_index',
               'sample_rate': 16000, 'origin_in_prepared_pts_sec': None}
        try:
            payload = path.read_bytes()
        except FileNotFoundError:
            payload = None
        if payload is None:
            row.update(status='missing', windows=[])
            missing.append(clip['clip_id'])
        else:
            windows = parse_prediction_text(payload.decode(), path.name)
            digest = hashlib.sha256(payload).hexdigest()
            if hashlib.sha256(historical_text(windows).encode()).hexdigest() != digest:
                raise ValueError(f'{path.name}: structured prediction round trip differs')
            row.update(status='observed' if windows else 'empty_file', windows=windows,
                       historical_text_sha256=digest)
            input_bytes += len(payload)
            if not windows:
                no_windows.append(clip['clip_id'])
            lengths[len(windows)] += 1
            counts['windows'] += len(windows)
            by_split[clip['split']]['windows'] += len(windows)
            for window in windows:
                if not window['labels']:
                    counts['windows_without_retained_labels'] += 1
                for label in window['labels']:
                    if label['mid'] not in label_map:
                        raise ValueError(f"Unknown label: {label['mid']}")
                    counts['retained_predictions'] += 1
                    labels[label['mid']] += 1
        counts[row['status']] += 1
        by_split[clip['split']][row['status']] += 1
        rows.append(row)
        if len(rows) % 1000 == 0:
            print(f'Validated {len(rows)}/{len(clips)} selected clips', flush=True)
    write_jsonl(output / 'audio_events.jsonl.gz', rows)
    write_jsonl(output / 'audio_event_labels.jsonl',
                ({'mid': mid, 'display_name': label_map[mid]} for mid in sorted(label_map)))
    provenance = {
        'input_kind': 'saved historical BEATs top-10 text predictions; no inference rerun',
        'inference_script_sha256': sha256(args.beats_workspace / 'test.py'),
        'label_map_sha256': sha256(label_path),
        'checkpoint_sha256': sha256(args.checkpoint),
        'window_length_sec': 10, 'hop_sec': 5, 'start_loop_stop_sec': 300,
        'sample_rate': 16000, 'top_k': 10, 'retention_threshold': 0.1,
        'probability_decimal_places': 4,
        'input_media': 'cropped_videos_at_25fps (historical script default)',
        'extraction': 'FFmpeg AAC decode to mono 16 kHz PCM s16le WAV; torchaudio.load',
        'coordinate_system': 'decoded_pcm_sample_index',
        'origin_in_prepared_pts_sec': None,
        'coordinate_caveat': 'Window zero is the first extracted WAV sample, not proven PTS zero. Do not silently join these times to video PTS.',
        'model_code': {name: sha256(args.beats_workspace / name) for name in
                       ('BEATs.py', 'backbone.py', 'modules.py')},
    }
    dump_json(output / 'audio_event_provenance.json', provenance)
    report = {'clips': len(clips), 'counts': dict(counts), 'by_split': {k:dict(v) for k,v in by_split.items()},
              'missing_clip_ids': missing, 'empty_file_clip_ids': no_windows,
              'windows_per_observed_clip': dict(sorted(lengths.items())),
              'historical_text_bytes': input_bytes, 'label_map_classes': len(label_map),
              'retained_label_classes': len(labels),
              'top_retained_labels': [{'mid': m, 'display_name': label_map[m], 'windows': n}
                                      for m,n in labels.most_common(20)],
              'all_prediction_records_validated': True,
              'historical_text_round_trip_exact': True}
    dump_json(output / 'audio_event_inventory.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in
                     ('missing_clip_ids','empty_file_clip_ids','top_retained_labels')}, indent=2))


if __name__ == '__main__':
    main()
