import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.export_audio_events import historical_text, parse_predictions


class AudioEventTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'clip.txt'
            path.write_text(text)
            return parse_predictions(path)

    def test_namespaces_empty_predictions_and_exact_text_round_trip(self):
        text = ('[0.0, 10.0] /m/09x0r,0.9000 /g/122z_qxw,0.2519 /t/dd00036,0.1000\n'
                '[5.0, 15.0]\n')
        windows = self.parse(text)
        self.assertEqual(windows[1]['labels'], [])
        self.assertEqual(historical_text(windows), text)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),
                         hashlib.sha256(historical_text(windows).encode()).hexdigest())

    def test_invalid_grid_probability_and_duplicate_label_fail(self):
        for text in ('[1.0, 11.0] /m/09x0r,0.9000\n',
                     '[0.0, 10.0] /m/09x0r,nan\n',
                     '[0.0, 10.0] /m/09x0r,0.0900\n',
                     '[0.0, 10.0] /m/09x0r,0.9000 /m/09x0r,0.8000\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)
