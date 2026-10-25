#!/usr/bin/env python3
"""Produce archive-separated RQ1 counts and within-archive proportions from Day 14."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


COMMUNITIES = ["ChatGPTCoding", "webdev", "programming", "GitHub", "compsci"]
LABELS = ["Trust", "Distrust", "Both", "Neither"]
DIMENSIONS = [
    "Competence", "Reliability", "Familiarity", "Integrity", "Transparency",
    "Benevolence", "Incompetence", "Unreliability", "Unfamiliarity",
    "Dishonesty", "Deception", "Opaqueness", "Malevolence",
]
PRIMARY_FIELD = "Output_gpt-4.1-2025-04-14_few"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def display_table(rows: list[dict], title: str) -> str:
    lines = [
        f"## {title}",
        "",
        "| Category | Count | Denominator | Within-archive proportion |",
        "| --- | ---: | ---: | ---: |",
    ]
    lines.extend(
        f"| {row['category']} | {row['count']:,} | {row['denominator_n']:,} | {row['within_archive_proportion']:.4%} |"
        for row in rows
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, required=True)
    parser.add_argument("--freeze-record", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True)

    freeze = json.loads(args.freeze_record.read_text(encoding="utf-8"))
    expected_classification_hash = freeze["artifacts"][args.classification.name]
    expected_dimensions_hash = freeze["artifacts"][args.dimensions.name]
    classification_hash = sha256(args.classification)
    dimensions_hash = sha256(args.dimensions)
    if classification_hash != expected_classification_hash:
        raise ValueError("classification frozen artifact hash does not match the Day 14 version record")
    if dimensions_hash != expected_dimensions_hash:
        raise ValueError("dimensions frozen artifact hash does not match the Day 14 version record")
    if set(freeze.get("decisions", [])) != {"D-013", "D-017", "D-018"}:
        raise ValueError("Day 14 record does not identify the required locked decisions")

    classification = read_jsonl(args.classification)
    dimensions = read_jsonl(args.dimensions)
    if len({row["id"] for row in classification}) != len(classification):
        raise ValueError("duplicate ID in classification freeze")
    if len({row["id"] for row in dimensions}) != len(dimensions):
        raise ValueError("duplicate ID in dimensions freeze")
    if len(classification) != 8520 or len(dimensions) != 4964:
        raise ValueError("Day 14 rows do not match the locked archive-specific totals")
    if any(row["community"] not in COMMUNITIES for row in classification + dimensions):
        raise ValueError("unexpected community in frozen input")

    class_source = Counter(row["community"] for row in classification)
    class_available = Counter(row["community"] for row in classification if row["label_status"] == "canonical")
    class_counts: dict[str, Counter] = {scope: Counter() for scope in ["ALL", *COMMUNITIES]}
    missing_ids = []
    for row in classification:
        if row["label_status"] == "canonical":
            if row["label"] not in LABELS:
                raise ValueError(f"unexpected canonical classification label: {row['label']}")
            class_counts["ALL"][row["label"]] += 1
            class_counts[row["community"]][row["label"]] += 1
        elif row["label_status"] == "missing":
            missing_ids.append(row["id"])
        else:
            raise ValueError("Day 15 permits no unaccounted noncanonical classification labels")

    dimension_n = Counter(row["community"] for row in dimensions)
    dimension_counts: dict[str, Counter] = {scope: Counter() for scope in ["ALL", *COMMUNITIES]}
    for row in dimensions:
        if row["dimension_field"] != PRIMARY_FIELD or row["encoding_status"] != "clean":
            raise ValueError("unexpected primary-field or parser status in dimensions freeze")
        for dimension in DIMENSIONS:
            if row[dimension] not in (0, 1):
                raise ValueError(f"nonbinary primary dimension encoding for {row['id']}: {dimension}")
            dimension_counts["ALL"][dimension] += row[dimension]
            dimension_counts[row["community"]][dimension] += row[dimension]

    rows = []
    denominator_rows = []
    for scope in ["ALL", *COMMUNITIES]:
        class_source_n = len(classification) if scope == "ALL" else class_source[scope]
        class_available_n = sum(class_available.values()) if scope == "ALL" else class_available[scope]
        dim_n = len(dimensions) if scope == "ALL" else dimension_n[scope]
        denominator_rows.extend([
            {
                "archive": "classification", "scope": scope, "source_or_eligible_n": class_source_n,
                "outcome_available_n": class_available_n, "missing_or_exception_n": class_source_n - class_available_n,
                "denominator_rule": "D-017: category shares use canonical-label-available N; source/funnel N retained separately.",
            },
            {
                "archive": "dimensions", "scope": scope, "source_or_eligible_n": dim_n,
                "outcome_available_n": dim_n, "missing_or_exception_n": 0,
                "denominator_rule": "D-013 primary field; all frozen rows have clean 13-token encodings.",
            },
        ])
        for label in LABELS:
            count = class_counts[scope][label]
            rows.append({
                "archive": "classification", "scope": scope, "category_type": "released_label", "category": label,
                "count": count, "denominator_type": "canonical_label_available", "denominator_n": class_available_n,
                "within_archive_proportion": count / class_available_n,
            })
        for dimension in DIMENSIONS:
            count = dimension_counts[scope][dimension]
            rows.append({
                "archive": "dimensions", "scope": scope, "category_type": "primary_dimension_indicator", "category": dimension,
                "count": count, "denominator_type": "primary_field_clean", "denominator_n": dim_n,
                "within_archive_proportion": count / dim_n,
            })

    checks = {
        "frozen_classification_hash_matches_day14_record": classification_hash == expected_classification_hash,
        "frozen_dimensions_hash_matches_day14_record": dimensions_hash == expected_dimensions_hash,
        "classification_source_n_is_8520": len(classification) == 8520,
        "classification_label_available_n_is_8519": sum(class_available.values()) == 8519,
        "classification_missing_label_count_is_1": len(missing_ids) == 1,
        "classification_category_counts_sum_to_8519": sum(class_counts["ALL"].values()) == 8519,
        "classification_scope_counts_match_available_denominators": all(
            sum(class_counts[scope].values()) == class_available[scope] for scope in COMMUNITIES
        ),
        "dimensions_primary_n_is_4964": len(dimensions) == 4964,
        "dimensions_all_rows_clean_primary_field": all(row["encoding_status"] == "clean" for row in dimensions),
        "dimensions_all_indicators_binary": all(
            row[dimension] in (0, 1) for row in dimensions for dimension in DIMENSIONS
        ),
        "no_cross_archive_join_performed": True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    if status != "PASS":
        raise RuntimeError(f"Day 15 QC failed: {checks}")

    results_path = args.output_dir / "rq1_counts_prevalence_source.csv"
    denominators_path = args.output_dir / "rq1_denominator_ledger.csv"
    write_csv(results_path, list(rows[0]), rows)
    write_csv(denominators_path, list(denominator_rows[0]), denominator_rows)

    all_classification = [row for row in rows if row["archive"] == "classification" and row["scope"] == "ALL"]
    all_dimensions = [row for row in rows if row["archive"] == "dimensions" and row["scope"] == "ALL"]
    report_path = args.output_dir / "day15_rq1_counts_prevalence.md"
    report_path.write_text(
        "# Day 15 — RQ1 archive-separated counts and within-archive proportions\n\n"
        "**Status:** PASS — mechanical descriptive output from the immutable Day 14 freeze. These are within-archive proportions of released records, not estimates of population prevalence or author attitudes.\n\n"
        "Classification and dimensions remain separate archives. The detailed source file includes the pooled and five community-specific rows; no ID join, confidence interval, statistical comparison, figure, or RQ interpretation was produced.\n\n"
        + display_table(all_classification, "Classification archive — pooled five-community records")
        + "\n\n"
        + display_table(all_dimensions, "Dimensions archive — pooled five-community primary field")
        + "\n\n"
        "**Denominator note:** Classification source/funnel `N=8,520`; category proportions use canonical-label-available `N=8,519`; one record remains missing and is retained in source accounting. Dimensions use the D-013 primary-field clean denominator `N=4,964`.\n",
        encoding="utf-8",
    )

    qc_path = args.output_dir / "qc_summary.json"
    qc_path.write_text(
        json.dumps({
            "status": status,
            "checks": checks,
            "scope": "Day 15 RQ1 archive-separated counts and within-archive proportions only.",
            "prohibited_or_deferred": ["cross-archive join", "confidence interval", "statistical comparison", "figure", "RQ interpretation"],
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_path = args.output_dir / "run_manifest.json"
    output_paths = [results_path, denominators_path, report_path, qc_path]
    manifest_path.write_text(
        json.dumps({
            "run_id": args.output_dir.name,
            "executed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "purpose": "Day 15 RQ1 counts and within-archive proportions using frozen Day 14 inputs only.",
            "inputs": {
                "day14_freeze_record": {"path": str(args.freeze_record), "sha256": sha256(args.freeze_record)},
                "classification_frozen": {"path": str(args.classification), "sha256": classification_hash, "rows": len(classification)},
                "dimensions_frozen": {"path": str(args.dimensions), "sha256": dimensions_hash, "rows": len(dimensions)},
            },
            "locked_rules": ["D-013 primary uniform field", "D-017 classification denominator", "D-019 archive separation"],
            "outputs": {path.name: sha256(path) for path in output_paths},
            "qc_status": status,
            "not_executed": ["confidence intervals", "table/figure publication display", "reliability sensitivity", "RQ1 freeze"],
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
