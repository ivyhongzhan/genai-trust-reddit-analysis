import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_package import verify

class PackageSmokeTest(unittest.TestCase):
    def test_frozen_artifact_and_scientific_checks(self):
        self.assertEqual(verify(), [])

if __name__ == '__main__':
    unittest.main()
