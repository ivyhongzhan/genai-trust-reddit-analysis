#!/usr/bin/env python3
"""Independently rerun RQ1 and community RQ2 from verified Day 14 JSONL inputs.

This does NOT recover original public JSON files, rerun Day 14 preprocessing,
regenerate temporal analyses, or reproduce figure rendering. The two required
record-level files are deliberately not redistributed with this repository.
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from reproduce_posthoc_association import calculate as association_from_community_table

ROOT = Path(__file__).resolve().parents[1]
RESULTS = {
    "rq1_counts": ("day15/rq1_counts_prevalence_source.csv", "results/rq1_counts_prevalence_source.csv", ("archive", "scope", "category")),
    "rq1_denominators": ("day15/rq1_denominator_ledger.csv", "results/rq1_denominator_ledger.csv", ("archive", "scope")),
    "community": ("day18/community_descriptive_summary.csv", "results/final_community_table_source.csv", ("archive", "community", "category")),
}
FLOAT_FIELDS = {"within_archive_proportion", "proportion"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def keyed_csv(path: Path, key_fields: tuple) -> tuple:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)) or not set(key_fields) <= set(columns):
            raise ValueError(f"missing columns in {path}")
        rows = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"malformed CSV row in {path}")
            key = tuple(row[field] for field in key_fields)
            if key in rows:
                raise ValueError(f"duplicate CSV key {key} in {path}")
            rows[key] = row
    return tuple(columns), rows


def compare_csv(actual: Path, frozen: Path, keys: tuple) -> dict:
    columns_a, rows_a = keyed_csv(actual, keys)
    columns_f, rows_f = keyed_csv(frozen, keys)
    errors = []
    if set(columns_a) != set(columns_f):
        errors.append(f"column mismatch: actual={columns_a} frozen={columns_f}")
    for key in sorted(set(rows_a) | set(rows_f)):
        if key not in rows_a or key not in rows_f:
            errors.append(f"missing/extra row: {key}")
            continue
        for field in sorted(set(rows_a[key]) & set(rows_f[key])):
            lhs, rhs = rows_a[key][field], rows_f[key][field]
            if field in FLOAT_FIELDS and not (lhs == rhs == ""):
                try:
                    ok = math.isfinite(float(lhs)) and math.isfinite(float(rhs)) and math.isclose(float(lhs), float(rhs), rel_tol=0, abs_tol=1e-12)
                except (ValueError, TypeError):
                    ok = False
            else:
                ok = lhs == rhs
            if not ok:
                errors.append(f"{key} {field}: computed={lhs!r} frozen={rhs!r}")
    return {"match": not errors, "computed_rows": len(rows_a), "frozen_rows": len(rows_f),
            "differences": errors[:30], "difference_count": len(errors)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory; never overwrites")
    parser.add_argument("--freeze-record", type=Path, default=ROOT / "provenance/data_freeze_version_record.json")
    parser.add_argument("--rq1-freeze-record", type=Path, default=ROOT / "provenance/rq1_freeze_record.json")
    args = parser.parse_args()
    freeze = json.loads(args.freeze_record.read_text(encoding="utf-8"))
    input_hashes = {}
    for key, path in (("classification", args.classification), ("dimensions", args.dimensions)):
        recorded = freeze["artifacts"][path.name]
        actual = sha256(path)
        if actual != recorded:
            parser.error(f"{key} input SHA-256 mismatch; no computation performed")
        input_hashes[key] = actual
    if args.output_dir.exists():
        parser.error("output directory already exists; choose a new directory")
    if args.rq1_freeze_record.resolve() == args.freeze_record.resolve():
        parser.error("RQ1 freeze and Day 14 freeze must be distinct")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    runs = [
        [sys.executable, str(ROOT / "scripts/run_day15_rq1_counts.py"),
         "--classification", str(args.classification.resolve()),
         "--dimensions", str(args.dimensions.resolve()),
         "--freeze-record", str(args.freeze_record.resolve()),
         "--output-dir", str((args.output_dir / "day15").resolve())],
        [sys.executable, str(ROOT / "scripts/run_day18_rq2_community.py"),
         "--classification", str(args.classification.resolve()),
         "--dimensions", str(args.dimensions.resolve()),
         "--freeze-record", str(args.freeze_record.resolve()),
         "--rq1-freeze-record", str(args.rq1_freeze_record.resolve()),
         "--output-dir", str((args.output_dir / "day18").resolve())],
    ]
    for run in runs:
        subprocess.run(run, cwd=ROOT, check=True)
    checks = {}
    for name, (derived, reference, keys) in RESULTS.items():
        checks[name] = compare_csv(args.output_dir / derived, ROOT / reference, keys)
    computed_association = association_from_community_table(args.output_dir / "day18/community_descriptive_summary.csv")
    frozen_association = association_from_community_table(ROOT / "results/final_community_table_source.csv")
    association_matches = (
        computed_association["n"] == frozen_association["n"]
        and math.isclose(computed_association["chi_square_descriptive"], frozen_association["chi_square_descriptive"], abs_tol=1e-12)
        and math.isclose(computed_association["cramers_v"], frozen_association["cramers_v"], abs_tol=1e-12)
        and all(math.isclose(computed_association["trust_minus_neither_percentage_points"][key], val, abs_tol=1e-12)
                for key, val in frozen_association["trust_minus_neither_percentage_points"].items())
    )
    success = all(check["match"] for check in checks.values()) and association_matches
    report = {
        "status": "PASS" if success else "FAIL",
        "scope": "Day 14 frozen record-level JSONL to Day 15 RQ1 and Day 18 community summaries only",
        "not_proven": ["original Zenodo source to Day 14 preprocessing", "Day 20 temporal summaries",
                       "RQ3 temporal/context outputs", "figure regeneration", "full raw-data-to-paper reproduction"],
        "verified_input_sha256": input_hashes,
        "comparison": checks,
        "association_from_regenerated_community_counts": {
            "match": association_matches,
            "computed": computed_association,
            "reference": frozen_association,
        },
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    with (args.output_dir / "reproduction_report.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(f"{report['status']}: Day 15 + Day 18 record-level rerun; report: {args.output_dir / 'reproduction_report.json'}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
