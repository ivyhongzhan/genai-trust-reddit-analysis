"""Safety checks for the public record-level workflow."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/reproduce_public.py'

class PublicWorkflowSafetyTests(unittest.TestCase):
    def test_modified_zip_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            zips = base / 'zips'
            zips.mkdir()
            (zips / 'Trust_Classification_json.zip').write_bytes(b'not the public archive')
            out = base / 'run'
            proc = subprocess.run([sys.executable, str(SCRIPT), '--zip-dir', str(zips), '--output-dir', str(out)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            report = json.loads((out / 'report.json').read_text())
            self.assertEqual(report['status'], 'FAIL')
            self.assertFalse(report['checks']['archive/classification_raw']['match'])
            self.assertFalse((out / 'raw/data_task1.json').exists())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / 'run'
            out.mkdir()
            marker = out / 'keep'
            marker.write_text('unchanged')
            proc = subprocess.run([sys.executable, str(SCRIPT), '--zip-dir', str(base), '--output-dir', str(out)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(marker.read_text(), 'unchanged')

if __name__ == '__main__':
    unittest.main()
