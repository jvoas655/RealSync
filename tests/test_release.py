import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from realsync.io import new_output_root, read_jsonl, safe_media_path, write_jsonl
from realsync.manifest import effective_offset, quantize_offset
from realsync.loader import read_window
from realsync.media import prepare
from realsync.evaluation import evaluate


class ReleaseTests(unittest.TestCase):
    def test_stable_gzip_and_float_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [{"offset_sec": -1.7987705805683816, "sample_id": "a"}]
            a, b = Path(tmp) / "a.gz", Path(tmp) / "b.gz"
            write_jsonl(a, rows)
            write_jsonl(b, rows)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(list(read_jsonl(a)), rows)

    def test_path_and_output_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inputs"
            root.mkdir()
            with self.assertRaises(ValueError):
                safe_media_path(root, "../other.mkv")
            with self.assertRaises(ValueError):
                new_output_root(root / "new", [root])
            output = Path(tmp) / "outputs"
            new_output_root(output, [root])
            with self.assertRaises(FileExistsError):
                new_output_root(output, [root])

    def test_offset_sign_and_grid(self):
        self.assertEqual(effective_offset(-1.7987705805683816), -1.8)
        self.assertEqual(quantize_offset(-2)[0], 0)
        self.assertEqual(quantize_offset(0)[0], 10)
        self.assertEqual(quantize_offset(2)[0], 20)

    def test_unknown_full_source_origin_refuses_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "inputs"
            inputs.mkdir()

            class IncompleteManifest:
                directory = root / "manifests"
                clips = {"clip": {"source_origin_sec": None}}

            output = root / "outputs"
            with self.assertRaises(ValueError):
                prepare(IncompleteManifest(), inputs, output, "full-sources")
            self.assertFalse(output.exists())

    def test_evaluation_coverage_and_metrics(self):
        class SmallManifest:
            def samples(self, split):
                return iter({"sample_id": str(i), "offset_class": i} for i in range(21))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "predictions.jsonl"
            rows = [
                {
                    "sample_id": str(i),
                    "logits": [10 if j == i else 0 for j in range(21)],
                }
                for i in range(21)
            ]
            write_jsonl(path, rows)
            result = evaluate(SmallManifest(), path)
            self.assertEqual(result["accuracy"], 1)
            self.assertEqual(result["mAP_present_classes"], 1)
            self.assertEqual(result["macro_roc_auc_present_classes"], 1)
            write_jsonl(path, rows[:-1])
            with self.assertRaises(ValueError):
                evaluate(SmallManifest(), path)
            result = evaluate(
                SmallManifest(), path, expected_ids=[str(i) for i in range(20)]
            )
            self.assertEqual(result["samples"], 20)

    def test_synthetic_reader_determinism_and_audio_offset(self):
        import numpy as np

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.mkv"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=256x256:rate=25:duration=8",
                    "-f",
                    "lavfi",
                    "-i",
                    "aevalsrc='sin(2*PI*(300*t+50*t*t))':s=16000:d=8",
                    "-c:v",
                    "libx264",
                    "-threads",
                    "1",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    str(path),
                ],
                check=True,
            )
            v, a = read_window(path, 2, 0.4, 1)
            v2, a2 = read_window(path, 2, 0.4, 1)
            np.testing.assert_array_equal(v, v2)
            np.testing.assert_array_equal(a, a2)
            shifted_v, shifted_a = read_window(path, 2.4, 0, 1)
            np.testing.assert_array_equal(a, shifted_a)
            self.assertEqual(v.shape, (25, 256, 256, 3))
            self.assertEqual(a.shape, (16000,))
            self.assertFalse(np.array_equal(v, shifted_v))
            with self.assertRaises(ValueError):
                read_window(path, 7, 0, 5)


if __name__ == "__main__":
    unittest.main()
