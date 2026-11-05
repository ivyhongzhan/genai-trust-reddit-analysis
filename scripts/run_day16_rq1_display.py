#!/usr/bin/env python3
"""Create the Day 16 RQ1 table and figure from verified Day 15 source data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from historical_figure_export import save_historical_vector


COMMUNITIES = ["ALL", "ChatGPTCoding", "webdev", "programming", "GitHub", "compsci"]
SCOPE_DISPLAY = {
    "ALL": "Pooled",
    "ChatGPTCoding": "ChatGPTCoding",
    "webdev": "webdev",
    "programming": "programming",
    "GitHub": "GitHub",
    "compsci": "compsci",
}
LABELS = ["Trust", "Distrust", "Both", "Neither"]
DIMENSIONS = [
    "Competence", "Reliability", "Familiarity", "Integrity", "Transparency",
    "Benevolence", "Incompetence", "Unreliability", "Unfamiliarity",
    "Dishonesty", "Deception", "Opaqueness", "Malevolence",
]
PRIMARY_FIELD = "Output_gpt-4.1-2025-04-14_few"
width_mm = 177.8
height_mm = 189.992


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def matrix(rows: list[dict], archive: str, categories: list[str]) -> tuple[np.ndarray, dict[tuple[str, str], dict]]:
    index = {
        (row["scope"], row["category"]): row
        for row in rows
        if row["archive"] == archive
    }
    values = np.array([
        [float(index[(scope, category)]["within_archive_proportion"]) * 100 for scope in COMMUNITIES]
        for category in categories
    ])
    return values, index


def markdown_section(title: str, categories: list[str], index: dict[tuple[str, str], dict]) -> str:
    header = "| Category | " + " | ".join(SCOPE_DISPLAY[scope] for scope in COMMUNITIES) + " |"
    rule = "| --- | " + " | ".join("---:" for _ in COMMUNITIES) + " |"
    body = []
    for category in categories:
        cells = []
        for scope in COMMUNITIES:
            row = index[(scope, category)]
            cells.append(
                f"{int(row['count']):,}/{int(row['denominator_n']):,} "
                f"({float(row['within_archive_proportion']) * 100:.1f}%)"
            )
        body.append("| " + category + " | " + " | ".join(cells) + " |")
    return f"## {title}\n\n{header}\n{rule}\n" + "\n".join(body)


def annotate_heatmap(ax: plt.Axes, values: np.ndarray) -> None:
    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            value = values[row_index, column_index]
            color = "white" if value >= 38 else "#202020"
            ax.text(
                column_index, row_index, f"{value:.1f}",
                ha="center", va="center", fontsize=6.2, color=color,
            )


def style_heatmap(ax: plt.Axes, values: np.ndarray, categories: list[str], title: str) -> mpl.image.AxesImage:
    image = ax.imshow(values, cmap="Blues", vmin=0, vmax=75, aspect="auto", interpolation="nearest")
    ax.set_yticks(np.arange(len(categories)), labels=categories)
    ax.set_xticks(np.arange(len(COMMUNITIES)), labels=[SCOPE_DISPLAY[scope] for scope in COMMUNITIES])
    ax.tick_params(axis="x", bottom=False, labelbottom=False, top=True, labeltop=True, length=0, pad=3)
    ax.tick_params(axis="y", length=0, pad=3)
    ax.set_title(title, loc="left", fontsize=8, fontweight="bold", pad=22)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(COMMUNITIES), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(categories), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    annotate_heatmap(ax, values)
    return image


def add_panel_label(ax: plt.Axes, label: str) -> None:
    from matplotlib.transforms import ScaledTranslation
    offset = ScaledTranslation(-18 / 72, 3 / 72, ax.figure.dpi_scale_trans)
    ax.text(
        0, 1, label, transform=ax.transAxes + offset,
        fontsize=9, fontweight="bold", ha="left", va="bottom",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day15-source", type=Path, required=True)
    parser.add_argument("--day15-manifest", type=Path, required=True)
    parser.add_argument("--figure-skill-scripts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    qa_dir = args.output_dir / "qa"
    qa_dir.mkdir()

    manifest = json.loads(args.day15_manifest.read_text(encoding="utf-8"))
    expected_hash = manifest["outputs"][args.day15_source.name]
    if sha256(args.day15_source) != expected_hash:
        raise ValueError("Day 15 source hash does not match its verified manifest")
    rows = list(csv.DictReader(args.day15_source.open(encoding="utf-8")))
    if len(rows) != 102:
        raise ValueError(f"expected 102 Day 15 source rows, found {len(rows)}")
    keys = {(row["archive"], row["scope"], row["category"]) for row in rows}
    if len(keys) != len(rows):
        raise ValueError("duplicate archive/scope/category row in Day 15 source")

    classification_values, classification_index = matrix(rows, "classification", LABELS)
    dimension_values, dimension_index = matrix(rows, "dimensions", DIMENSIONS)
    if not np.allclose(classification_values.sum(axis=0), 100, atol=1e-9):
        raise ValueError("classification percentages do not sum to 100 within scope")

    table_source_rows = []
    for row in rows:
        table_source_rows.append({
            **row,
            "percentage": f"{float(row['within_archive_proportion']) * 100:.6f}",
            "display": f"{int(row['count'])}/{int(row['denominator_n'])} ({float(row['within_archive_proportion']) * 100:.1f}%)",
        })
    table_source_path = args.output_dir / "rq1_table_source.csv"
    write_csv(table_source_path, list(table_source_rows[0]), table_source_rows)

    table_path = args.output_dir / "rq1_table.md"
    table_path.write_text(
        "# Table 2 | RQ1 composition of released classification labels and trust/distrust dimensions\n\n"
        "Values are exact `n/N (%)` finite-archive summaries. No confidence intervals or inferential tests are reported under D-020.\n\n"
        + markdown_section("A. Released classification labels", LABELS, classification_index)
        + "\n\n"
        + markdown_section("B. Primary-field dimensions", DIMENSIONS, dimension_index)
        + "\n\n"
        "**Notes:** Classification category denominators are label-available records; the complete source/funnel contains 8,520 records and retains one missing label. Dimensions use the clean primary-field denominator from the separate 4,964-record dimensions archive. Dimension indicators may co-occur and do not sum to 100%. `Pooled` denotes the five prespecified communities combined. These values describe released sampled discourse records, not population prevalence or author attitudes.\n",
        encoding="utf-8",
    )

    contract_path = args.output_dir / "figure_contract.md"
    contract_path.write_text(
        "# Figure contract\n\n"
        "- **Core conclusion:** Released classification labels and trust/distrust dimensions have distinct finite-archive composition across the pooled corpus and five sampled communities.\n"
        "- **Results-level question:** What label and dimension composition is observed for RQ1 overall and within each sampled community?\n"
        "- **Archetype:** Quantitative grid.\n"
        "- **Backend:** Python/matplotlib.\n"
        "- **Final size:** 177.8 mm × 189.992 mm.\n"
        "- **Panel a:** Four mutually exclusive released classification labels; label-available denominators.\n"
        "- **Panel b:** Thirteen co-occurring primary-field dimension indicators; clean dimensions-archive denominators.\n"
        "- **Evidence hierarchy:** Both panels are necessary and archive-separated; panel a characterizes classification composition, panel b characterizes multidimensional composition.\n"
        "- **Statistics:** Exact counts and within-archive proportions only; no confidence intervals or tests under D-020.\n"
        "- **Reviewer risks:** Prevent archive conflation, population-prevalence interpretation, author-level inference, and the false implication that dimensions are mutually exclusive.\n",
        encoding="utf-8",
    )

    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams.update({'svg.fonttype': 'none', 'pdf.fonttype': 42})
    plt.rcParams["font.size"] = 7
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"

    # Preserve the original rendered canvas recorded in frozen alignment QA:
    # width_pt=504.0, height_pt=538.5600000000001.
    width_in = 7.0
    height_in = 7.48
    fig = plt.figure(figsize=(width_in, height_in), constrained_layout=False)
    grid = fig.add_gridspec(2, 1, height_ratios=[4.3, 13.3], hspace=0.33, left=0.22, right=0.91, top=0.92, bottom=0.07)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[1, 0])
    image = style_heatmap(ax_a, classification_values, LABELS, "Released classification labels")
    style_heatmap(ax_b, dimension_values, DIMENSIONS, "Primary-field trust/distrust dimensions")
    ax_b.axhline(5.5, color="#5F5F5F", linewidth=0.8)
    add_panel_label(ax_a, "a")
    add_panel_label(ax_b, "b")
    colorbar_ax = fig.add_axes([0.935, 0.18, 0.018, 0.64], label="<colorbar-rq1>")
    colorbar = fig.colorbar(image, cax=colorbar_ax)
    colorbar.set_label("Within-archive proportion (%)", fontsize=7)
    colorbar.ax.tick_params(labelsize=6, length=2)
    fig.text(
        0.22, 0.015,
        "Exact finite-archive proportions; no confidence intervals. Classification and dimensions remain separate archives.",
        ha="left", va="bottom", fontsize=6.2, color="#3F3F3F",
    )
    fig.canvas.draw()

    sys.path.insert(0, str(args.figure_skill_scripts))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    alignment_path = qa_dir / "rq1_figure.alignment.json"
    alignment_overlay = qa_dir / "rq1_figure.alignment.svg"
    require_matplotlib_panel_alignment(
        fig,
        axes=[ax_a, ax_b],
        panel_ids={ax_a: "a", ax_b: "b"},
        column_groups=[{"id": "shared-community-columns", "panels": ["a", "b"]}],
        json_out=alignment_path,
        overlay_svg=alignment_overlay,
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=True,
        strict=True,
    )

    figure_stem = args.output_dir / "rq1_figure"
    # Historical reference remains separate from the new >=300 dpi export.
    save_historical_vector(fig, figure_stem)
    high_resolution_stem = args.output_dir / "rq1_figure_300dpi"
    fig.savefig(high_resolution_stem.with_suffix(".svg"), dpi=320, bbox_inches="tight")
    fig.savefig(high_resolution_stem.with_suffix(".pdf"), dpi=320, bbox_inches="tight")
    fig.savefig(figure_stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(figure_stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)

    legend_path = args.output_dir / "rq1_figure_legend.md"
    legend_path.write_text(
        "**Fig. 1 | Composition of released trust/distrust labels and dimensions across sampled technical communities.** "
        "**a,** Within-archive proportions of the four mutually exclusive released classification labels in the pooled five-community archive and each community; cells show percentages among records with a canonical label. "
        "**b,** Within-archive proportions of the 13 co-occurring trust/distrust dimension indicators in the separate dimensions archive, encoded from the locked primary field; cells show percentages among clean primary-field records. "
        "The classification source/funnel contains 8,520 records, including one retained missing label, and category proportions use 8,519 label-available records. The dimensions archive contains 4,964 clean primary-field records. "
        "No confidence intervals or inferential tests are shown under D-020. Values describe released sampled discourse records, not population prevalence or author attitudes. Source data are provided in `rq1_table_source.csv`.\n",
        encoding="utf-8",
    )

    checks = {
        "day15_source_hash_matches_manifest": True,
        "source_rows_are_102": len(rows) == 102,
        "classification_percentages_sum_to_100_by_scope": True,
        "classification_and_dimensions_archives_remain_separate": True,
        "no_confidence_intervals_or_tests": True,
        "table_contains_all_pooled_and_community_rows": len(table_source_rows) == 102,
        "figure_contains_all_classification_labels": classification_values.shape == (4, 6),
        "figure_contains_all_dimensions": dimension_values.shape == (13, 6),
        "panel_alignment_gate_passed": True,
    }
    qc_path = args.output_dir / "qc_summary.json"
    qc_path.write_text(json.dumps({
        "status": "PASS",
        "checks": checks,
        "table": "rq1_table.md",
        "figure": ["rq1_figure.svg", "rq1_figure.pdf", "rq1_figure.tiff", "rq1_figure.png"],
        "uncertainty_rule": "D-020: exact finite-archive counts/proportions; no confidence intervals or inferential tests.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_paths = [
        table_source_path, table_path, contract_path,
        figure_stem.with_suffix(".svg"), figure_stem.with_suffix(".pdf"),
        figure_stem.with_suffix(".tiff"), figure_stem.with_suffix(".png"),
        high_resolution_stem.with_suffix(".svg"), high_resolution_stem.with_suffix(".pdf"),
        legend_path, alignment_path, alignment_overlay, qc_path,
    ]
    run_manifest_path = args.output_dir / "run_manifest.json"
    run_manifest_path.write_text(json.dumps({
        "run_id": args.output_dir.name,
        "executed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "purpose": "Day 16 RQ1 manuscript table and two-panel figure under D-020; no Day 15 or Day 17 rerun.",
        "input": {"path": str(args.day15_source), "sha256": sha256(args.day15_source), "rows": len(rows)},
        "locked_rules": ["D-013", "D-017", "D-019", "D-020"],
        "backend": "Python/matplotlib",
        "figure_size_mm": [width_mm, height_mm],
        "outputs": {str(path.relative_to(args.output_dir)): sha256(path) for path in output_paths},
        "qc_status": "PASS_PENDING_RENDERED_PDF_AUDITS",
        "not_executed": ["Day 15", "Day 17", "RQ1 freeze", "Day 18 or later work"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
