#!/usr/bin/env python3
"""Create archive-separated Day 18 RQ2 community descriptions and heatmap inputs."""

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


def cell_text(row: dict) -> str:
    return f"{row['count']:,}/{row['eligible_denominator_n']:,} ({row['proportion']:.2%})"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, required=True)
    parser.add_argument("--freeze-record", type=Path, required=True)
    parser.add_argument("--rq1-freeze-record", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    script_path = Path(__file__).resolve()

    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True)

    freeze = json.loads(args.freeze_record.read_text(encoding="utf-8"))
    rq1_freeze = json.loads(args.rq1_freeze_record.read_text(encoding="utf-8"))
    classification_hash = sha256(args.classification)
    dimensions_hash = sha256(args.dimensions)
    expected_classification_hash = freeze["artifacts"][args.classification.name]
    expected_dimensions_hash = freeze["artifacts"][args.dimensions.name]
    if freeze.get("freeze_id") != "20260925_day14_archive_separated_freeze_v1":
        raise ValueError("unexpected D-019 freeze identifier")
    if classification_hash != expected_classification_hash or dimensions_hash != expected_dimensions_hash:
        raise ValueError("frozen input hash does not match D-019 version record")
    if rq1_freeze.get("status") != "PASS":
        raise ValueError("frozen RQ1 provenance anchor is not PASS")

    classification = read_jsonl(args.classification)
    dimensions = read_jsonl(args.dimensions)
    if len(classification) != 8520 or len(dimensions) != 4964:
        raise ValueError("archive-specific row totals do not match D-019")
    if len({row["id"] for row in classification}) != len(classification):
        raise ValueError("duplicate classification ID in frozen input")
    if len({row["id"] for row in dimensions}) != len(dimensions):
        raise ValueError("duplicate dimensions ID in frozen input")
    if {row["community"] for row in classification} != set(COMMUNITIES):
        raise ValueError("classification communities differ from the prespecified set")
    if {row["community"] for row in dimensions} != set(COMMUNITIES):
        raise ValueError("dimensions communities differ from the prespecified set")

    class_source_n = Counter(row["community"] for row in classification)
    class_available_n = Counter()
    class_missing_n = Counter()
    class_counts = {community: Counter() for community in COMMUNITIES}
    missing_ids: list[str] = []
    for row in classification:
        community = row["community"]
        if row["label_status"] == "canonical":
            if row["label"] not in LABELS:
                raise ValueError(f"unexpected canonical label: {row['label']}")
            class_available_n[community] += 1
            class_counts[community][row["label"]] += 1
        elif row["label_status"] == "missing":
            class_missing_n[community] += 1
            missing_ids.append(row["id"])
        else:
            raise ValueError(f"unexpected classification label status: {row['label_status']}")

    dimension_source_n = Counter(row["community"] for row in dimensions)
    dimension_counts = {community: Counter() for community in COMMUNITIES}
    for row in dimensions:
        if row["dimension_field"] != PRIMARY_FIELD or row["encoding_status"] != "clean":
            raise ValueError("frozen dimensions row violates D-013 field/parser status")
        for dimension in DIMENSIONS:
            value = row[dimension]
            if value not in (0, 1):
                raise ValueError(f"nonbinary indicator for {row['id']}: {dimension}")
            dimension_counts[row["community"]][dimension] += value

    summary_rows: list[dict] = []
    denominator_rows: list[dict] = []
    for community in COMMUNITIES:
        denominator_rows.extend([
            {
                "archive": "classification",
                "community": community,
                "source_n": class_source_n[community],
                "eligible_denominator_n": class_available_n[community],
                "missing_or_exception_n": class_missing_n[community],
                "denominator_type": "canonical_label_available",
                "rule": "D-017",
            },
            {
                "archive": "dimensions",
                "community": community,
                "source_n": dimension_source_n[community],
                "eligible_denominator_n": dimension_source_n[community],
                "missing_or_exception_n": 0,
                "denominator_type": "primary_field_clean",
                "rule": "D-013",
            },
        ])
        for label in LABELS:
            count = class_counts[community][label]
            denominator = class_available_n[community]
            summary_rows.append({
                "archive": "classification",
                "community": community,
                "category_type": "released_label",
                "category": label,
                "count": count,
                "eligible_denominator_n": denominator,
                "proportion_fraction": f"{count}/{denominator}",
                "proportion": count / denominator,
                "denominator_type": "canonical_label_available",
                "missing_or_exception_n": class_missing_n[community],
                "field": "LLM_Predictions",
            })
        for dimension in DIMENSIONS:
            count = dimension_counts[community][dimension]
            denominator = dimension_source_n[community]
            summary_rows.append({
                "archive": "dimensions",
                "community": community,
                "category_type": "primary_dimension_indicator",
                "category": dimension,
                "count": count,
                "eligible_denominator_n": denominator,
                "proportion_fraction": f"{count}/{denominator}",
                "proportion": count / denominator,
                "denominator_type": "primary_field_clean",
                "missing_or_exception_n": 0,
                "field": PRIMARY_FIELD,
            })

    summary_path = args.output_dir / "community_descriptive_summary.csv"
    denominator_path = args.output_dir / "community_denominator_ledger.csv"
    write_csv(summary_path, list(summary_rows[0]), summary_rows)
    write_csv(denominator_path, list(denominator_rows[0]), denominator_rows)

    lookup = {(row["archive"], row["category"], row["community"]): row for row in summary_rows}
    matrix_rows: list[dict] = []
    for archive, category_type, categories in [
        ("classification", "released_label", LABELS),
        ("dimensions", "primary_dimension_indicator", DIMENSIONS),
    ]:
        for category in categories:
            matrix_row = {
                "archive": archive,
                "category_type": category_type,
                "category": category,
                "value": "within_archive_eligible_proportion",
            }
            for community in COMMUNITIES:
                matrix_row[community] = f"{lookup[(archive, category, community)]['proportion']:.12f}"
            matrix_rows.append(matrix_row)
    matrix_path = args.output_dir / "heatmap_source_matrix.csv"
    write_csv(matrix_path, ["archive", "category_type", "category", "value", *COMMUNITIES], matrix_rows)

    class_lines = [
        "# Day 18 classification community summary",
        "",
        "| Community | Source N | Eligible N | Missing | Trust | Distrust | Both | Neither |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for community in COMMUNITIES:
        row_map = {label: lookup[("classification", label, community)] for label in LABELS}
        class_lines.append(
            f"| {community} | {class_source_n[community]:,} | {class_available_n[community]:,} | "
            f"{class_missing_n[community]:,} | " + " | ".join(cell_text(row_map[label]) for label in LABELS) + " |"
        )
    class_lines.extend([
        "",
        "Category proportions use the D-017 canonical-label-available denominator within each community. "
        "Source counts and the retained missing-label count remain visible.",
    ])
    class_table_path = args.output_dir / "classification_community_summary.md"
    class_table_path.write_text("\n".join(class_lines) + "\n", encoding="utf-8")

    dim_lines = [
        "# Day 18 dimensions community summary",
        "",
        "Each cell is `count/eligible N (proportion)` for the D-013 primary field. Indicators are multi-label and do not sum to 100%.",
        "",
        "| Dimension | " + " | ".join(COMMUNITIES) + " |",
        "| --- | " + " | ".join(["---:"] * len(COMMUNITIES)) + " |",
    ]
    for dimension in DIMENSIONS:
        dim_lines.append(
            f"| {dimension} | "
            + " | ".join(cell_text(lookup[("dimensions", dimension, community)]) for community in COMMUNITIES)
            + " |"
        )
    dim_lines.extend([
        "",
        f"Field: `{PRIMARY_FIELD}`. All frozen rows are parser-clean under the locked 13-token vocabulary.",
    ])
    dim_table_path = args.output_dir / "dimensions_community_summary.md"
    dim_table_path.write_text("\n".join(dim_lines) + "\n", encoding="utf-8")

    heatmap_spec_path = args.output_dir / "heatmap_specification.md"
    heatmap_spec_path.write_text(
        "# Day 18 RQ2 community heatmap specification\n\n"
        "## Role\n\n"
        "Prepare one archive-separated quantitative grid with two visibly separated panels: "
        "classification labels and primary-field dimensions. This artifact specifies a later render; Day 18 does not render the figure.\n\n"
        "## Source and ordering\n\n"
        "- Source matrix: `heatmap_source_matrix.csv`; exact cell counts and denominators: `community_descriptive_summary.csv`.\n"
        "- Community columns, fixed: `ChatGPTCoding`, `webdev`, `programming`, `GitHub`, `compsci`.\n"
        "- Classification rows, fixed: `Trust`, `Distrust`, `Both`, `Neither`.\n"
        "- Dimension rows, fixed to the D-013 13-token order recorded in the source matrix.\n"
        f"- Dimension field: `{PRIMARY_FIELD}`.\n\n"
        "## Cell encoding\n\n"
        "- Fill value: exact within-community eligible proportion from the relevant archive.\n"
        "- Cell label: `count/eligible N` plus percentage; source/missing information remains in the denominator ledger and caption.\n"
        "- Use a declared sequential 0–1 scale and an explicit legend labeled `Within-archive proportion`.\n"
        "- Do not encode missing or exception rows as category/dimension absence.\n\n"
        "## Required annotations\n\n"
        "- Classification: D-017 canonical-label-available denominator, with source N and retained missing count disclosed for every community.\n"
        "- Dimensions: D-013 primary-field clean denominator; indicators are multi-label and rows do not sum to 100%.\n"
        "- State that the archives are separate and that the display describes released sampled discourse records, not people or population prevalence.\n\n"
        "## Prohibited additions\n\n"
        "No pooled column, time bin, cross-archive combination, uncertainty interval, significance marker, ranking claim, or substantive interpretation is part of Day 18.\n",
        encoding="utf-8",
    )

    checks = {
        "classification_hash_matches_d019": classification_hash == expected_classification_hash,
        "dimensions_hash_matches_d019": dimensions_hash == expected_dimensions_hash,
        "rq1_freeze_anchor_pass": rq1_freeze.get("status") == "PASS",
        "classification_source_n_is_8520": len(classification) == 8520,
        "classification_available_n_is_8519": sum(class_available_n.values()) == 8519,
        "classification_missing_label_count_is_1": len(missing_ids) == 1,
        "classification_counts_reconcile_by_community": all(
            sum(class_counts[c].values()) == class_available_n[c] for c in COMMUNITIES
        ),
        "dimensions_source_n_is_4964": len(dimensions) == 4964,
        "dimensions_all_primary_field_clean": all(
            row["dimension_field"] == PRIMARY_FIELD and row["encoding_status"] == "clean" for row in dimensions
        ),
        "dimensions_all_indicators_binary": all(
            row[d] in (0, 1) for row in dimensions for d in DIMENSIONS
        ),
        "summary_rows_are_85": len(summary_rows) == 85,
        "denominator_rows_are_10": len(denominator_rows) == 10,
        "heatmap_matrix_rows_are_17": len(matrix_rows) == 17,
        "classification_proportions_sum_to_one_by_community": all(
            abs(sum(lookup[("classification", label, c)]["proportion"] for label in LABELS) - 1.0) < 1e-12
            for c in COMMUNITIES
        ),
        "archives_remain_separate": True,
        "no_temporal_summary_produced": True,
        "no_inferential_or_model_output": True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    if status != "PASS":
        raise RuntimeError(f"Day 18 QC failed: {checks}")

    provenance_path = args.output_dir / "provenance_record.json"
    provenance_path.write_text(json.dumps({
        "run_id": args.output_dir.name,
        "scope": "Day 18 archive-separated community descriptions and heatmap preparation only.",
        "rules": ["D-013", "D-017", "D-019"],
        "inputs": {
            "execution_script": {"path": str(script_path), "sha256": sha256(script_path)},
            "d019_freeze_record": {"path": str(args.freeze_record), "sha256": sha256(args.freeze_record)},
            "classification_frozen": {"path": str(args.classification), "sha256": classification_hash, "rows": len(classification)},
            "dimensions_frozen": {"path": str(args.dimensions), "sha256": dimensions_hash, "rows": len(dimensions)},
            "rq1_freeze_record": {"path": str(args.rq1_freeze_record), "sha256": sha256(args.rq1_freeze_record)},
        },
        "archive_relationship": "separate; no row-level join or shared denominator",
        "not_executed": [
            "temporal summaries", "model", "hypothesis test", "effect size", "BH/FDR", "RQ2 freeze", "Day 19 or later"
        ],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    qc_path = args.output_dir / "qc_summary.json"
    qc_path.write_text(json.dumps({
        "status": status,
        "checks": checks,
        "row_counts": {
            "community_descriptive_summary": len(summary_rows),
            "community_denominator_ledger": len(denominator_rows),
            "heatmap_source_matrix": len(matrix_rows),
        },
        "scope": "Day 18 community summaries and heatmap preparation only.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_paths = [
        summary_path, denominator_path, matrix_path, class_table_path, dim_table_path,
        heatmap_spec_path, provenance_path, qc_path,
    ]
    manifest_path = args.output_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps({
        "run_id": args.output_dir.name,
        "executed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "purpose": "Day 18 RQ2 archive-separated community summaries and heatmap preparation.",
        "locked_rules": ["D-013", "D-017", "D-019"],
        "inputs": {
            "execution_script": {"path": str(script_path), "sha256": sha256(script_path)},
            "d019_freeze_record": {"path": str(args.freeze_record), "sha256": sha256(args.freeze_record)},
            "classification_frozen": {"path": str(args.classification), "sha256": classification_hash},
            "dimensions_frozen": {"path": str(args.dimensions), "sha256": dimensions_hash},
            "rq1_freeze_record": {"path": str(args.rq1_freeze_record), "sha256": sha256(args.rq1_freeze_record)},
        },
        "outputs": {str(path.relative_to(args.output_dir)): sha256(path) for path in output_paths},
        "qc_status": status,
        "not_executed": [
            "temporal summaries", "model", "hypothesis test", "effect size", "BH/FDR", "RQ2 freeze", "Day 19 or later"
        ],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
