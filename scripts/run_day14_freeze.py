#!/usr/bin/env python3
"""Create the archive-separated Day 14 freeze package without a cross-archive join."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


COMMUNITIES = ["ChatGPTCoding", "webdev", "programming", "GitHub", "compsci"]
COMMUNITY_BY_CASEFOLD = {community.casefold(): community for community in COMMUNITIES}
LABELS = {"Trust", "Distrust", "Both", "Neither"}
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


def half_year(timestamp: int) -> tuple[str, str]:
    dt = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    half = "H1" if dt.month <= 6 else "H2"
    bin_name = f"{dt.year}-{half}"
    status = "partial_coverage_not_comparable" if bin_name == "2022-H2" else "primary_comparison_window"
    return bin_name, status


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, required=True)
    parser.add_argument("--day11-encoding", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    classification_all = json.loads(args.classification.read_text(encoding="utf-8"))
    dimensions_all = json.loads(args.dimensions.read_text(encoding="utf-8"))
    day11_encoding = {row["id"]: row for row in (json.loads(line) for line in args.day11_encoding.read_text(encoding="utf-8").splitlines())}

    classification_rows = []
    for source in classification_all:
        community = COMMUNITY_BY_CASEFOLD.get(str(source.get("subreddit", "")).casefold())
        if community is None:
            continue
        raw = source.get("LLM_Predictions")
        label = "" if raw is None else str(raw).strip()
        label_status = "canonical" if label in LABELS else ("missing" if not label else "noncanonical")
        bin_name, bin_status = half_year(source["created_utc"])
        classification_rows.append({
            "id": source["id"], "subreddit_source": source["subreddit"], "community": community,
            "created_utc": source["created_utc"], "half_year_utc": bin_name,
            "half_year_status": bin_status, "label_raw": raw, "label": label if label_status == "canonical" else None,
            "label_status": label_status,
        })

    dimension_rows = []
    for source in dimensions_all:
        community = COMMUNITY_BY_CASEFOLD.get(str(source.get("subreddit", "")).casefold())
        if community is None:
            continue
        prior = day11_encoding.get(source["id"])
        if prior is None:
            raise ValueError(f"dimension ID missing from Day 11 encoding: {source['id']}")
        if prior["field"] != PRIMARY_FIELD or prior["raw_output"] != source.get(PRIMARY_FIELD):
            raise ValueError(f"Day 11 field/output mismatch: {source['id']}")
        if prior["encoding_status"] != "clean":
            raise ValueError(f"non-clean primary encoding: {source['id']}")
        bin_name, bin_status = half_year(source["created_utc"])
        dimension_rows.append({
            "id": source["id"], "subreddit_source": source["subreddit"], "community": community,
            "created_utc": source["created_utc"], "half_year_utc": bin_name,
            "half_year_status": bin_status, "dimension_field": PRIMARY_FIELD,
            "dimension_raw": source.get(PRIMARY_FIELD), "encoding_status": prior["encoding_status"],
            **{dimension: prior[dimension] for dimension in DIMENSIONS},
        })

    if len(classification_rows) != 8520 or len(dimension_rows) != 4964:
        raise ValueError(f"unexpected frozen row counts: {len(classification_rows)}, {len(dimension_rows)}")
    if {row['id'] for row in dimension_rows} != set(day11_encoding):
        raise ValueError("Day 11 encoding IDs and frozen dimension IDs differ")
    if sum(row["label_status"] == "canonical" for row in classification_rows) != 8519:
        raise ValueError("classification canonical-label count is not 8519")

    classification_path = args.output_dir / "classification_analytic_frozen.jsonl"
    dimensions_path = args.output_dir / "dimensions_analytic_frozen.jsonl"
    write_jsonl(classification_path, classification_rows)
    write_jsonl(dimensions_path, dimension_rows)

    missing_rows = [row for row in classification_rows if row["label_status"] == "missing"]
    if len(missing_rows) != 1:
        raise ValueError("expected exactly one missing classification label")
    missing_id = missing_rows[0]["id"]

    table_rows = [
        {
            "archive_stage": "Classification: five-community source/funnel",
            "eligibility_rule": "Five prespecified communities; released LLM_Predictions retained.",
            "records": 8520, "available_outcome": 8519, "missing_exception": f"1 missing label ({missing_id})",
            "denominator": "Source/funnel N=8,520; category shares N=8,519", "provenance": "D-017; raw classification SHA-256",
        },
        {
            "archive_stage": "Dimensions: five-community primary-field encoding",
            "eligibility_rule": "Five prespecified communities; D-013 primary field parsed under locked 13-token vocabulary.",
            "records": 4964, "available_outcome": 4964, "missing_exception": "0 missing/empty/unexpected/duplicate-token rows",
            "denominator": "Primary-field eligible N=4,964", "provenance": "D-013; Day 11 v2; raw dimensions SHA-256",
        },
    ]
    table_source = args.output_dir / "table1_analytic_sample_summary_source.csv"
    write_csv(table_source, list(table_rows[0]), table_rows)
    table_markdown = args.output_dir / "table1_analytic_sample_summary.md"
    table_markdown.write_text(
        "# Table 1 — Analytic sample and QC summary\n\n"
        "This QC ledger freezes separate classification and dimensions archives. It does not imply a joined dataset.\n\n"
        "| Archive / stage | Eligibility rule | Records | Available outcome | Missing / exception | Denominator used | Provenance note |\n"
        "| --- | --- | ---: | ---: | --- | --- | --- |\n"
        + "\n".join(
            f"| {r['archive_stage']} | {r['eligibility_rule']} | {r['records']} | {r['available_outcome']} | {r['missing_exception']} | {r['denominator']} | {r['provenance']} |"
            for r in table_rows
        )
        + "\n\n**Footnote:** Classification and dimensions remain archive-specific. `2022-H2` is retained as partial-coverage context only; primary temporal comparisons use `2023-H1`–`2025-H1`.\n",
        encoding="utf-8",
    )

    analysis_plan = args.output_dir / "analysis_plan_v2.md"
    analysis_plan.write_text(
        "# Analysis plan v2 — frozen Day 14 implementation record\n\n"
        "**Status:** Frozen implementation plan; no RQ result, figure, model, or cross-archive join is produced by this record.\n\n"
        "## Locked inputs and rules\n\n"
        f"- Classification archive: five-community source/funnel `N=8,520`; category shares use canonical-label `N=8,519`; `{missing_id}` remains missing (D-017).\n"
        "- Dimensions archive: five-community primary field `Output_gpt-4.1-2025-04-14_few`, `N=4,964`, parsed with the D-013 exact 13-token vocabulary.\n"
        "- Time: UTC half-years; `2022-H2` is partial-coverage context only; primary comparisons use `2023-H1`–`2025-H1`; observed `N<20` cells are insufficient and zero-count cells unavailable (D-018).\n"
        "- Reporting: keep archives separate; no automatic join, temporal model, uncertainty interval, or causal/author-level inference.\n\n"
        "## Deferred branches\n\n"
        "Archive alignment, uncertainty displays, models, and result interpretation remain outside this freeze and require their own approvals.\n",
        encoding="utf-8",
    )
    deviations = args.output_dir / "deviation_log.md"
    deviations.write_text(
        "# Day 14 deviation log\n\n"
        "- **No Day 14 deviation from locked rules.** The freeze is archive-separated; no join, row deletion, recoding, temporal model, uncertainty interval, figure, or RQ interpretation was performed.\n"
        "- **Prior preserved correction:** Day 11 v1 had a display-normalization defect for source `github`; v2 corrected it and is the only Day 11 input used here.\n"
        "- **Locked temporal boundary:** `2022-H2` is retained as partial-coverage context only under D-018; it is not a primary comparison bin.\n",
        encoding="utf-8",
    )

    artifact_names = [
        classification_path.name, dimensions_path.name, table_source.name,
        table_markdown.name, analysis_plan.name, deviations.name,
    ]
    version = {
        "freeze_id": args.output_dir.name,
        "scope": "Archive-separated descriptive analytic freeze; no join, model, interval, figure, or RQ interpretation.",
        "decisions": ["D-013", "D-017", "D-018"],
        "inputs": {
            "classification_raw": {"path": str(args.classification), "sha256": sha256(args.classification), "source_rows": len(classification_all), "frozen_rows": len(classification_rows)},
            "dimensions_raw": {"path": str(args.dimensions), "sha256": sha256(args.dimensions), "source_rows": len(dimensions_all), "frozen_rows": len(dimension_rows)},
            "day11_primary_encoding": {"path": str(args.day11_encoding), "sha256": sha256(args.day11_encoding), "rows": len(day11_encoding)},
        },
        "artifacts": {name: sha256(args.output_dir / name) for name in artifact_names},
        "excluded_from_freeze": ["cross-archive join", "uncertainty display", "model", "figure", "RQ interpretation"],
    }
    (args.output_dir / "data_freeze_version_record.json").write_text(json.dumps(version, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
