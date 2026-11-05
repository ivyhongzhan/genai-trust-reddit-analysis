"""Unit tests for independently computed descriptive results and CSV comparator."""
import csv
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from reproduce_posthoc_association import calculate, COMMUNITIES, LABELS
from reproduce_frozen_inputs import compare_csv


class AssociationTests(unittest.TestCase):
    def setUp(self):
        self.counts = [
            [2300, 934, 87, 2011],
            [650, 314, 33, 1014],
            [237, 74, 3, 199],
            [134, 62, 2, 180],
            [87, 43, 4, 151],
        ]

    def make_csv(self, path, delete_cell=False):
        with path.open("w", newline="", encoding="utf-8") as h:
            writer = csv.DictWriter(h, fieldnames=["archive", "community", "category", "count", "eligible_denominator_n", "denominator_type"])
            writer.writeheader()
            for community, row in zip(COMMUNITIES, self.counts):
                for label, value in zip(LABELS, row):
                    if delete_cell and community == "compsci" and label == "Both":
                        continue
                    writer.writerow({"archive": "classification", "community": community, "category": label,
                                     "count": value, "eligible_denominator_n": sum(row),
                                     "denominator_type": "canonical_label_available"})

    def test_published_contingency_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "community.csv"
            self.make_csv(path)
            actual = calculate(path)
            self.assertEqual(actual["n"], 8519)
            self.assertAlmostEqual(actual["chi_square_descriptive"], 137.5163864065677)
            self.assertAlmostEqual(actual["cramers_v"], 0.07335374468450037)
            self.assertAlmostEqual(actual["trust_minus_neither_percentage_points"]["programming"], 7.407407407407407)

    def test_committed_frozen_community_counts(self):
        published = calculate(ROOT / "results/final_community_table_source.csv")
        self.assertEqual(published["n"], 8519)
        self.assertAlmostEqual(published["chi_square_descriptive"], 137.5163864065677)
        self.assertAlmostEqual(published["cramers_v"], 0.07335374468450037)

    def test_missing_cell_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            self.make_csv(path, delete_cell=True)
            with self.assertRaises(ValueError):
                calculate(path)


class ComparisonTests(unittest.TestCase):
    def test_unavailable_is_preserved_and_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "new.csv", Path(tmp) / "frozen.csv"
            a.write_text("archive,scope,category,count,proportion\ndimensions,A,Competence,0,\n")
            b.write_text(a.read_text())
            self.assertTrue(compare_csv(a, b, ("archive", "scope", "category"))["match"])
            b.write_text("archive,scope,category,count,proportion\ndimensions,A,Competence,0,0.0\n")
            self.assertFalse(compare_csv(a, b, ("archive", "scope", "category"))["match"])

    def test_malformed_and_nonfinite_values_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "new.csv", Path(tmp) / "frozen.csv"
            b.write_text("archive,scope,category,proportion\nclassification,A,Trust,0.4\n")
            for text in ["archive,scope,category,proportion\nclassification,A,Trust\n",
                         "archive,scope,category,proportion,proportion\nclassification,A,Trust,0.4,0.4\n",
                         "archive,scope,category,proportion\nclassification,A,Trust,0.4,extra\n"]:
                a.write_text(text)
                with self.assertRaises(ValueError):
                    compare_csv(a, b, ("archive", "scope", "category"))
            for value in ["inf", "nan", "-inf"]:
                a.write_text("archive,scope,category,proportion\nclassification,A,Trust," + value + "\n")
                b.write_text(a.read_text())
                self.assertFalse(compare_csv(a, b, ("archive", "scope", "category"))["match"])

    def test_row_order_and_float_precision(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "new.csv", Path(tmp) / "frozen.csv"
            a.write_text("archive,scope,category,count,proportion\nclassification,A,Trust,3,0.30000000000000004\nclassification,A,Neither,7,0.7\n")
            b.write_text("archive,scope,category,count,proportion\nclassification,A,Neither,7,0.7\nclassification,A,Trust,3,0.3\n")
            self.assertTrue(compare_csv(a, b, ("archive", "scope", "category"))["match"])
            b.write_text("archive,scope,category,count,proportion\nclassification,A,Neither,7,0.7\nclassification,A,Trust,4,0.3\n")
            self.assertFalse(compare_csv(a, b, ("archive", "scope", "category"))["match"])


class InputSafetyTests(unittest.TestCase):
    def test_wrong_frozen_hash_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            classification = tmp / "classification_analytic_frozen.jsonl"
            dimensions = tmp / "dimensions_analytic_frozen.jsonl"
            classification.write_text("{}\n")
            dimensions.write_text("{}\n")
            output = tmp / "new-output"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/reproduce_frozen_inputs.py"),
                "--classification", str(classification), "--dimensions", str(dimensions),
                "--output-dir", str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 mismatch", result.stderr)
            self.assertFalse(output.exists())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            output = tmp / "existing"
            output.mkdir()
            marker = output / "sentinel"
            marker.write_bytes(b"preserve")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/reproduce_end_to_end.py"),
                "--research-root", str(tmp / "inputs"), "--manuscript-root", str(tmp / "paper"),
                "--figure-qa-scripts", str(tmp / "qa"), "--output-dir", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing overwrite", result.stderr)
            self.assertEqual(marker.read_bytes(), b"preserve")
            self.assertEqual(list(output.iterdir()), [marker])


if __name__ == "__main__":
    unittest.main()
