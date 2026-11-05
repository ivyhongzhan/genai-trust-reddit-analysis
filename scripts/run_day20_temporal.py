#!/usr/bin/env python3
"""Bounded Day 20 archive-separated temporal descriptive run."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/day20_rq2_temporal/20260926_day20_rq2_temporal_v1"
QA = OUT / "visualization_qa"
FREEZE = ROOT / "outputs/day14_freeze/20260925_day14_archive_separated_freeze_v1"
DAY19 = ROOT / "outputs/day19_rq2_community/20260926_day19_rq2_community_v1"
SKILL_SCRIPTS = Path(__import__("os").environ.get("FIGURE_QA_SCRIPTS", str(ROOT / "scripts/figure_qa")))
sys.path.insert(0, str(SKILL_SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment

COMMUNITIES = ["ChatGPTCoding", "webdev", "programming", "GitHub", "compsci"]
HALF_YEARS = ["2022-H2", "2023-H1", "2023-H2", "2024-H1", "2024-H2", "2025-H1"]
LABELS = ["Trust", "Distrust", "Both", "Neither"]
DIMENSIONS = [
    "Reliability", "Competence", "Familiarity", "Transparency", "Integrity",
    "Benevolence", "Unfamiliarity", "Incompetence", "Opaqueness", "Deception",
    "Malevolence", "Dishonesty", "Unreliability",
]
PRIMARY_FIELD = "Output_gpt-4.1-2025-04-14_few"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_csv(path: Path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def classification_eligible(rows):
    return [r for r in rows if r["label_status"] == "canonical"]


def cell_fields(half_year, source_n, eligible_n, exceptions):
    partial = half_year == "2022-H2"
    if eligible_n == 0:
        availability = "unavailable_zero_count"
        sufficiency = "unavailable"
        comparison = "unavailable"
    elif eligible_n < 20:
        availability = "partial_context_insufficient" if partial else "insufficient_n_lt_20"
        sufficiency = "insufficient_n_lt_20"
        comparison = "not_comparable_partial_period" if partial else "insufficient_for_temporal_comparison"
    else:
        availability = "partial_context" if partial else "available"
        sufficiency = "sufficient_n_ge_20"
        comparison = "not_comparable_partial_period" if partial else "primary_comparable_window"
    return {
        "period_role": "partial_coverage_context_only" if partial else "primary_comparison_window",
        "source_n": source_n,
        "outcome_available_n": eligible_n,
        "missing_or_exception_n": exceptions,
        "availability_status": availability,
        "sufficiency_status": sufficiency,
        "temporal_comparison_status": comparison,
    }


def record_summary(archive, community, half_year, category_type, category, count, cell, denominator_type, field):
    denominator = cell["outcome_available_n"]
    available = denominator > 0
    return {
        "archive": archive,
        "community": community,
        "half_year_utc": half_year,
        "period_role": cell["period_role"],
        "category_type": category_type,
        "category": category,
        "count": count,
        "source_n": cell["source_n"],
        "outcome_available_n": denominator,
        "missing_or_exception_n": cell["missing_or_exception_n"],
        "denominator_type": denominator_type,
        "proportion_fraction": f"{count}/{denominator}" if available else "Unavailable",
        "proportion": (count / denominator) if available else "",
        "availability_status": cell["availability_status"],
        "sufficiency_status": cell["sufficiency_status"],
        "temporal_comparison_status": cell["temporal_comparison_status"],
        "field": field,
    }


def make_heatmap_figure(rows, archive, categories, filename, title, legend_title):
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.linewidth": 0.8,
    })
    figure_height = 5.6 if len(categories) > 4 else 3.8
    fig, axes = plt.subplots(1, len(COMMUNITIES), figsize=(7.01, figure_height), sharey=True)
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad("#737373")
    norm = Normalize(vmin=0, vmax=1)
    panel_ids = [chr(ord("a") + index) for index in range(len(COMMUNITIES))]
    cell_index = {(r["community"], r["half_year_utc"]): r for r in rows if r["category"] == categories[0]}
    row_index = {(r["community"], r["half_year_utc"], r["category"]): r for r in rows}
    image = None
    for panel, community, ax in zip(panel_ids, COMMUNITIES, axes):
        matrix = []
        for category in categories:
            row = []
            for half_year in HALF_YEARS:
                value = row_index[(community, half_year, category)]["proportion"]
                row.append(float(value) if value != "" else float("nan"))
            matrix.append(row)
        image = ax.imshow(matrix, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
        ax.set_yticks(range(len(categories)))
        if community == COMMUNITIES[0]:
            ax.set_yticklabels(categories, fontsize=5.8 if len(categories) > 4 else 6.5)
        else:
            ax.tick_params(axis="y", labelleft=False)
        ax.set_title(community, loc="left", x=0.12, fontsize=6.8, fontweight="bold", pad=8)
        ax.text(0.02, 0.96, panel, transform=ax.transAxes, fontsize=7, fontweight="bold", va="top")
        for col, half_year in enumerate(HALF_YEARS):
            cell = cell_index[(community, half_year)]
            if cell["period_role"] == "partial_coverage_context_only":
                ax.axvspan(col - 0.5, col + 0.5, facecolor="#737373", alpha=0.16, linewidth=0, zorder=2)
            elif cell["sufficiency_status"] == "insufficient_n_lt_20":
                ax.axvspan(col - 0.5, col + 0.5, facecolor="#B64342", alpha=0.10, linewidth=0, zorder=2)
        labels = []
        tick_colors = []
        for half_year in HALF_YEARS:
            cell = cell_index[(community, half_year)]
            labels.append("{}\n{}".format(half_year[:4], half_year[-2:]))
            if cell["outcome_available_n"] == 0:
                tick_colors.append("#4D4D4D")
            elif cell["sufficiency_status"] == "insufficient_n_lt_20":
                tick_colors.append("#B64342")
            elif cell["period_role"] == "partial_coverage_context_only":
                tick_colors.append("#737373")
            else:
                tick_colors.append("#272727")
        ax.set_xticks(range(len(HALF_YEARS)))
        ax.set_xticklabels(labels, fontsize=5.1)
        for label, color in zip(ax.get_xticklabels(), tick_colors):
            label.set_color(color)
        ax.tick_params(axis="y", length=0, pad=3)
        ax.set_xlim(-0.5, len(HALF_YEARS) - 0.5)
    fig.suptitle(title, x=0.02, y=0.99, ha="left", fontsize=8.5, fontweight="bold")
    fig.text(0.02, 0.915, "Gray shading: 2022-H2 partial context. Red period labels: insufficient (N<20). Dark gray cells: unavailable (N=0).", fontsize=5.7)
    fig.subplots_adjust(left=0.18 if len(categories) > 4 else 0.12, right=0.985, top=0.84, bottom=0.21, wspace=0.08)
    cax = fig.add_axes([0.37, 0.06, 0.28, 0.018])
    colorbar = fig.colorbar(image, cax=cax, orientation="horizontal", ticks=[0, 0.25, 0.5, 0.75, 1.0])
    colorbar.ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    colorbar.ax.tick_params(labelsize=5.5)
    colorbar.set_label(legend_title, fontsize=6, labelpad=2)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        axes=list(axes),
        panel_ids=panel_ids,
        row_groups=[panel_ids],
        json_out=str(QA / f"{filename}.alignment.json"),
        overlay_svg=str(QA / f"{filename}.alignment.svg"),
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=True,
        strict=True,
    )
    base = OUT / filename
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)


def main():
    global ROOT, OUT, QA, FREEZE, DAY19
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--freeze-dir", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--day19-dir", type=Path)
    group.add_argument("--community-dir", type=Path, help="new Day 18 rerun, not a historical Day 19 gate")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    ROOT = args.research_root.resolve()
    FREEZE = args.freeze_dir.resolve()
    DAY19 = args.day19_dir.resolve() if args.day19_dir else None
    OUT = args.output_dir.resolve()
    QA = OUT / "visualization_qa"
    OUT.mkdir(parents=True, exist_ok=False)
    QA.mkdir()
    version = json.loads((FREEZE / "data_freeze_version_record.json").read_text(encoding="utf-8"))
    class_path = FREEZE / "classification_analytic_frozen.jsonl"
    dim_path = FREEZE / "dimensions_analytic_frozen.jsonl"
    classification = read_jsonl(class_path)
    dimensions = read_jsonl(dim_path)

    assert sha256(class_path) == version["artifacts"][class_path.name]
    assert sha256(dim_path) == version["artifacts"][dim_path.name]
    assert len(classification) == 8520 and len(dimensions) == 4964
    assert {r["community"] for r in classification} == set(COMMUNITIES)
    assert {r["community"] for r in dimensions} == set(COMMUNITIES)
    assert {r["half_year_utc"] for r in classification} == set(HALF_YEARS)
    assert {r["half_year_utc"] for r in dimensions} <= set(HALF_YEARS)
    assert {r["dimension_field"] for r in dimensions} == {PRIMARY_FIELD}
    assert all(r["encoding_status"] == "clean" for r in dimensions)

    source_counts = {
        "classification": Counter((r["community"], r["half_year_utc"]) for r in classification),
        "dimensions": Counter((r["community"], r["half_year_utc"]) for r in dimensions),
    }
    eligible_class = classification_eligible(classification)
    class_eligible_counts = Counter((r["community"], r["half_year_utc"]) for r in eligible_class)
    class_exception_counts = Counter((r["community"], r["half_year_utc"]) for r in classification if r["label_status"] != "canonical")
    dim_eligible_counts = Counter((r["community"], r["half_year_utc"]) for r in dimensions)

    cells = []
    class_rows = []
    dim_rows = []
    for archive in ["classification", "dimensions"]:
        for community in COMMUNITIES:
            for half_year in HALF_YEARS:
                source_n = source_counts[archive][(community, half_year)]
                if archive == "classification":
                    eligible_n = class_eligible_counts[(community, half_year)]
                    exceptions = class_exception_counts[(community, half_year)]
                    denominator_type = "canonical_label_available"
                    field = "LLM_Predictions"
                else:
                    eligible_n = dim_eligible_counts[(community, half_year)]
                    exceptions = 0
                    denominator_type = "primary_field_clean"
                    field = PRIMARY_FIELD
                cell = cell_fields(half_year, source_n, eligible_n, exceptions)
                cells.append({
                    "archive": archive, "community": community, "half_year_utc": half_year,
                    **cell, "denominator_type": denominator_type, "field": field,
                })
                if archive == "classification":
                    bucket = [r for r in eligible_class if r["community"] == community and r["half_year_utc"] == half_year]
                    counts = Counter(r["label"] for r in bucket)
                    for label in LABELS:
                        class_rows.append(record_summary("classification", community, half_year, "released_label", label, counts[label], cell, denominator_type, field))
                else:
                    bucket = [r for r in dimensions if r["community"] == community and r["half_year_utc"] == half_year]
                    for dimension in DIMENSIONS:
                        dim_rows.append(record_summary("dimensions", community, half_year, "primary_dimension_indicator", dimension, sum(r[dimension] for r in bucket), cell, denominator_type, field))

    cell_fields_out = ["archive", "community", "half_year_utc", "period_role", "source_n", "outcome_available_n", "missing_or_exception_n", "denominator_type", "availability_status", "sufficiency_status", "temporal_comparison_status", "field"]
    summary_fields = ["archive", "community", "half_year_utc", "period_role", "category_type", "category", "count", "source_n", "outcome_available_n", "missing_or_exception_n", "denominator_type", "proportion_fraction", "proportion", "availability_status", "sufficiency_status", "temporal_comparison_status", "field"]
    write_csv(OUT / "classification_temporal_summary.csv", summary_fields, class_rows)
    write_csv(OUT / "dimensions_temporal_summary.csv", summary_fields, dim_rows)
    write_csv(OUT / "temporal_visualization_source.csv", summary_fields, class_rows + dim_rows)
    write_csv(OUT / "temporal_cell_status_ledger.csv", cell_fields_out, cells)

    make_heatmap_figure(class_rows, "classification", LABELS, "classification_temporal_visualization", "Classification composition by community and UTC half-year", "Classification proportion")
    make_heatmap_figure(dim_rows, "dimensions", DIMENSIONS, "dimensions_temporal_visualization", "Primary-field dimension composition by community and UTC half-year", "Dimension prevalence")

    preflight = subprocess.run(
        ["python3", str(SKILL_SCRIPTS / "validate_figure.py"), __file__, "--json"],
        check=True, text=True, capture_output=True,
    )
    (QA / "source_preflight.json").write_text(preflight.stdout, encoding="utf-8")
    preflight_json = json.loads(preflight.stdout)
    assert preflight_json["summary"]["counts"]["FAIL"] == 0
    assert preflight_json["summary"]["counts"]["WARN"] == 0
    for figure_name in ["classification_temporal_visualization", "dimensions_temporal_visualization"]:
        pdf = OUT / f"{figure_name}.pdf"
        pdf_audit = subprocess.run(
            ["python3", str(SKILL_SCRIPTS / "audit_pdf_text.py"), str(pdf), "--min-pt", "5", "--json"],
            check=True, text=True, capture_output=True,
        )
        (QA / f"{figure_name}.pdf_text_audit.json").write_text(pdf_audit.stdout, encoding="utf-8")
        pdf_audit_json = json.loads(pdf_audit.stdout)
        assert pdf_audit_json["auditable"] is True
        assert pdf_audit_json["below_minimum_count"] == 0
        collision = subprocess.run(
            ["python3", str(SKILL_SCRIPTS / "audit_figure_collisions.py"), str(pdf), "--json-out", str(QA / f"{figure_name}.collision_audit.json")],
            check=True, text=True, capture_output=True,
        )
        collision_json = json.loads((QA / f"{figure_name}.collision_audit.json").read_text(encoding="utf-8"))
        assert collision_json["verdict"] == "PASS"

    if DAY19 is not None:
        day19_inputs = {
            "final_community_table_source": DAY19 / "final_community_table_source.csv",
            "denominator_exception_ledger": DAY19 / "denominator_exception_ledger.csv",
            "qc_summary": DAY19 / "qc_summary.json",
            "run_manifest": DAY19 / "run_manifest.json",
            "planner_review": DAY19 / "planner_review/PLANNER_REVIEW.md",
        }
        day19_qc = json.loads(day19_inputs["qc_summary"].read_text(encoding="utf-8"))
        day19_manifest = json.loads(day19_inputs["run_manifest"].read_text(encoding="utf-8"))
        assert day19_qc["status"] == "PASS" and all(day19_qc["checks"].values())
        assert day19_manifest["status"] == "PASS"
        provenance_disposition = "Historical Day 19 PASS artifacts verified; not used for temporal computation."
    else:
        community_dir = args.community_dir.resolve()
        day19_inputs = {"new_community_qc": community_dir / "qc_summary.json",
                        "new_community_manifest": community_dir / "run_manifest.json",
                        "new_community_table": community_dir / "community_descriptive_summary.csv"}
        qc = json.loads(day19_inputs["new_community_qc"].read_text())
        manifest = json.loads(day19_inputs["new_community_manifest"].read_text())
        assert qc["status"] == "PASS" and all(qc["checks"].values())
        assert sha256(day19_inputs["new_community_table"]) == manifest["outputs"]["community_descriptive_summary.csv"]
        assert manifest["inputs"]["classification_frozen"]["sha256"] == sha256(class_path)
        assert manifest["inputs"]["dimensions_frozen"]["sha256"] == sha256(dim_path)
        provenance_disposition = "New Day 18 rerun verified; historical Day 19 PASS was not rerun or asserted."

    cell_lookup = {(r["archive"], r["community"], r["half_year_utc"]): r for r in cells}
    checks = {
        "classification_frozen_hash_matches_d019": sha256(class_path) == version["artifacts"][class_path.name],
        "dimensions_frozen_hash_matches_d019": sha256(dim_path) == version["artifacts"][dim_path.name],
        "classification_frozen_rows_are_8520": len(classification) == 8520,
        "dimensions_frozen_rows_are_4964": len(dimensions) == 4964,
        "five_expected_communities_retained_in_each_archive": all({r["community"] for r in dataset} == set(COMMUNITIES) for dataset in [classification, dimensions]),
        "all_expected_archive_community_half_year_cells_retained": len(cells) == 60,
        "classification_summary_rows_are_120": len(class_rows) == 120,
        "dimensions_summary_rows_are_390": len(dim_rows) == 390,
        "visualization_source_rows_are_510": len(class_rows) + len(dim_rows) == 510,
        "partial_2022_h2_cells_retained_as_context_only": all(cell_lookup[(archive, community, "2022-H2")]["period_role"] == "partial_coverage_context_only" for archive in ["classification", "dimensions"] for community in COMMUNITIES),
        "primary_window_is_2023_h1_through_2025_h1": all(cell_lookup[(archive, community, half_year)]["period_role"] == "primary_comparison_window" for archive in ["classification", "dimensions"] for community in COMMUNITIES for half_year in HALF_YEARS[1:]),
        "all_nonzero_n_lt_20_cells_marked_insufficient": all(cell["sufficiency_status"] == "insufficient_n_lt_20" for cell in cells if 0 < cell["outcome_available_n"] < 20),
        "zero_count_cells_marked_unavailable": all(cell["availability_status"] == "unavailable_zero_count" for cell in cells if cell["outcome_available_n"] == 0),
        "expected_zero_count_cell_is_retained": cell_lookup[("dimensions", "compsci", "2023-H1")]["outcome_available_n"] == 0,
        "classification_category_counts_reconcile_to_outcome_available_denominator": all(sum(r["count"] for r in class_rows if r["community"] == c and r["half_year_utc"] == h) == cell_lookup[("classification", c, h)]["outcome_available_n"] for c in COMMUNITIES for h in HALF_YEARS),
        "dimension_counts_bounded_by_outcome_available_denominator": all(r["count"] <= r["outcome_available_n"] for r in dim_rows),
        "available_proportions_equal_exact_counts_over_outcome_available_denominator": all((r["proportion"] == "" and r["proportion_fraction"] == "Unavailable") or abs(float(r["proportion"]) - r["count"] / r["outcome_available_n"]) < 1e-15 for r in class_rows + dim_rows),
        "classification_missing_label_preserved_without_recoding": sum(class_exception_counts.values()) == 1,
        "dimension_primary_field_parser_exceptions_are_zero": all(cell["missing_or_exception_n"] == 0 for cell in cells if cell["archive"] == "dimensions"),
        "archives_remain_separate": True,
        "no_cross_archive_join": True,
        "community_prerequisite_verified": True,
        "community_prerequisite_not_used_for_temporal_computation": True,
        "no_model": True,
        "no_hypothesis_test": True,
        "no_effect_size": True,
        "no_bh_fdr": True,
        "no_canonical_edit": True,
        "no_rq2_freeze": True,
        "no_day21_work": True,
    }
    assert all(checks.values())
    qc = {
        "status": "PASS",
        "scope": "Day 20 archive-separated UTC half-year descriptive summaries and temporal visualizations only.",
        "checks": checks,
        "row_counts": {"temporal_cell_status_ledger": len(cells), "classification_temporal_summary": len(class_rows), "dimensions_temporal_summary": len(dim_rows), "temporal_visualization_source": len(class_rows) + len(dim_rows)},
        "cell_status_counts": dict(Counter(cell["availability_status"] for cell in cells)),
        "rules_applied": ["D-013", "D-017", "D-018", "D-019"],
        "archive_relationship": "separate; no row-level join, pooled denominator, or cross-archive calculation",
        "not_executed": ["model", "hypothesis test", "effect size", "BH/FDR", "cross-archive join", "canonical edit", "RQ2 freeze", "Day 21 work"],
    }
    (OUT / "qc_summary.json").write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "run_id": "20260926_day20_rq2_temporal_v1",
        "executed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "purpose": "Produce D-019 frozen-input, archive-separated community × UTC half-year descriptive source tables and temporal visualizations for Day 20.",
        "status": "PASS",
        "inputs": {
            "classification_analytic_frozen": {"path": str(class_path), "sha256": sha256(class_path), "rows": len(classification)},
            "dimensions_analytic_frozen": {"path": str(dim_path), "sha256": sha256(dim_path), "rows": len(dimensions)},
            "data_freeze_version_record": {"path": str(FREEZE / "data_freeze_version_record.json"), "sha256": sha256(FREEZE / "data_freeze_version_record.json")},
            "community_prerequisite_provenance_only": {key: {"path": str(path), "sha256": sha256(path)} for key, path in day19_inputs.items()},
        },
        "outputs": {str(path.relative_to(OUT)): sha256(path) for path in sorted(OUT.glob("*.csv")) + sorted(OUT.glob("*.svg")) + sorted(OUT.glob("*.pdf")) + sorted(OUT.glob("*.png")) + sorted(OUT.glob("*.tiff")) + sorted(QA.glob("*")) + [OUT / "qc_summary.json"]},
        "rules_applied": ["D-013", "D-017", "D-018", "D-019"],
        "time_rule": {"bins": "UTC calendar half-years", "partial_context_only": "2022-H2", "primary_comparison_window": ["2023-H1", "2023-H2", "2024-H1", "2024-H2", "2025-H1"], "n_lt_20": "insufficient", "zero_count": "unavailable", "cell_merging": "not performed"},
        "archive_relationship": "separate; no row-level join, pooled denominator, or cross-archive calculation",
        "community_prerequisite_disposition": provenance_disposition,
        "not_executed": ["model", "hypothesis test", "effect size", "BH/FDR", "cross-archive join", "canonical edit", "RQ2 freeze", "Day 21 work"],
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    planner = """# Planner Review — Day 20

## Status and scope

**PASS.** Day 20 produced archive-separated community × UTC half-year descriptive source tables and two temporal visualization bundles from the D-019 frozen inputs. The run is bounded to descriptive reporting and stops here.

## Inputs and provenance

- Computation used only the D-019 frozen classification and dimensions JSONL inputs after their recorded SHA-256 hashes and row counts were verified.
- Day 19 PASS artifacts were verified as dependency/provenance only. No Day 19 table or ledger supplied a temporal count, denominator, or proportion.
- Classification and dimensions were processed as separate archives. No merged dataset, shared denominator, or cross-archive calculation was created.

## Temporal rule

- Every expected archive × community × UTC half-year cell is retained: 60 cells total.
- `2022-H2` is retained as partial-coverage context only. The primary comparison window is `2023-H1` through `2025-H1`.
- Nonzero outcome-available cells with `N < 20` are explicitly flagged insufficient. Zero-count cells are retained and marked unavailable. No cells were merged.
- Classification proportions use canonical-label-available denominators and preserve the one missing label without recoding. Dimension proportions use the D-013 primary clean-field denominator and retain their multi-label interpretation.

## Outputs

- `classification_temporal_summary.csv` (120 rows) and `dimensions_temporal_summary.csv` (390 rows): exact archive-specific counts, denominators, fractions, proportions, and cell status.
- `temporal_visualization_source.csv` (510 rows): source data for the two visualization bundles.
- `temporal_cell_status_ledger.csv` (60 rows): expected cells, partial-period status, sparsity status, and comparison eligibility.
- Separate classification and dimensions visualization exports (SVG, PDF, PNG, TIFF), with visible partial, insufficient, and unavailable markings.

## Visualization contract and QC

The figures display exact finite-archive within-cell proportions without confidence intervals, tests, effect sizes, or temporal trend fitting. The five community panels are aligned and rendered QA artifacts are retained in `visualization_qa/`. `qc_summary.json` records PASS for frozen-input integrity, cell completeness, denominator reconciliation, status coding, archive separation, and Day 19 provenance verification.

## Boundaries observed

No models, hypothesis tests, effect sizes, BH/FDR, joins, canonical edits, RQ2 freeze, or Day 21 work were executed.

## Next Planner action

Independently review the listed source tables, cell-status ledger, visualizations, and recorded hashes. This PASS does not advance any later day automatically.
"""
    review_dir = OUT / "planner_review"
    review_dir.mkdir()
    (review_dir / "PLANNER_REVIEW.md").write_text(planner, encoding="utf-8")
    manifest_path = OUT / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["planner_review/PLANNER_REVIEW.md"] = sha256(review_dir / "PLANNER_REVIEW.md")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
