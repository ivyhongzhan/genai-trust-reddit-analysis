#!/usr/bin/env python3
"""Execute D-021 denominator sensitivity and the evidence-limited reliability disposition."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


COMMUNITIES = ["ChatGPTCoding", "webdev", "programming", "GitHub", "compsci"]
COMMUNITY_BY_CASEFOLD = {value.casefold(): value for value in COMMUNITIES}
LABELS = ["Trust", "Distrust", "Both", "Neither"]
DIMENSIONS = [
    "Competence", "Reliability", "Familiarity", "Integrity", "Transparency",
    "Benevolence", "Incompetence", "Unreliability", "Unfamiliarity",
    "Dishonesty", "Deception", "Opaqueness", "Malevolence",
]
PRIMARY_FIELD = "Output_gpt-4.1-2025-04-14_few"
SENSITIVITY_FIELDS = [
    "Output_gpt-4.1-2025-04-14",
    "Output_gpt-4.1-nano-2025-04-14",
    "Output_gpt-4.1-nano-2025-04-14_few",
    "Output_gpt-4o-2024-11-20",
    "Output_gpt-5-mini-2025-08-07",
    "Output_gpt-5-mini-2025-08-07_few",
]
FIELDS = [PRIMARY_FIELD, *SENSITIVITY_FIELDS]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_dimension(raw: object) -> dict:
    if raw is None or not str(raw).strip():
        return {
            "status": "unknown", "reason": "missing", "tokens": [],
            "empty_tokens": [], "duplicate_tokens": [], "unexpected_tokens": [],
        }
    tokens = [token.strip() for token in str(raw).split(",")]
    empty_tokens = [token for token in tokens if not token]
    duplicate_tokens = sorted(token for token, count in Counter(tokens).items() if token and count > 1)
    unexpected_tokens = sorted({token for token in tokens if token and token not in DIMENSIONS})
    reasons = []
    if empty_tokens:
        reasons.append("empty_token")
    if duplicate_tokens:
        reasons.append("duplicate_token")
    if unexpected_tokens:
        reasons.append("unexpected_token")
    return {
        "status": "clean" if not reasons else "unknown",
        "reason": ";".join(reasons) if reasons else "",
        "tokens": tokens,
        "empty_tokens": empty_tokens,
        "duplicate_tokens": duplicate_tokens,
        "unexpected_tokens": unexpected_tokens,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification-frozen", type=Path, required=True)
    parser.add_argument("--dimensions-raw", type=Path, required=True)
    parser.add_argument("--day14-record", type=Path, required=True)
    parser.add_argument("--day11-manifest", type=Path, required=True)
    parser.add_argument("--day11-field-qc", type=Path, required=True)
    parser.add_argument("--day15-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True)

    day14 = json.loads(args.day14_record.read_text(encoding="utf-8"))
    day11 = json.loads(args.day11_manifest.read_text(encoding="utf-8"))
    if sha256(args.classification_frozen) != day14["artifacts"][args.classification_frozen.name]:
        raise ValueError("classification freeze hash mismatch")
    if sha256(args.dimensions_raw) != day11["inputs"]["dimensions"]["sha256"]:
        raise ValueError("dimensions raw hash mismatch")
    if day11["primary_dimension_field"] != PRIMARY_FIELD or day11["sensitivity_fields"] != SENSITIVITY_FIELDS:
        raise ValueError("Day 11 field order/specification mismatch")

    classification = read_jsonl(args.classification_frozen)
    dimensions_all = json.loads(args.dimensions_raw.read_text(encoding="utf-8"))
    dimensions = [
        row for row in dimensions_all
        if str(row.get("subreddit", "")).casefold() in COMMUNITY_BY_CASEFOLD
    ]
    day15_rows = list(csv.DictReader(args.day15_source.open(encoding="utf-8")))
    day11_qc = {
        row["field"]: row
        for row in csv.DictReader(args.day11_field_qc.open(encoding="utf-8"))
    }

    if len(classification) != 8520 or len(dimensions) != 4964:
        raise ValueError("archive-specific row counts do not match the locked freeze")

    scopes = ["ALL", *COMMUNITIES]
    sensitivity_rows: list[dict] = []
    exception_rows: list[dict] = []

    for scope in scopes:
        records = classification if scope == "ALL" else [row for row in classification if row["community"] == scope]
        source_n = len(records)
        eligible = [row for row in records if row["label_status"] == "canonical"]
        unknown = [row for row in records if row["label_status"] != "canonical"]
        if scope == "ALL":
            for row in unknown:
                exception_rows.append({
                    "archive": "classification", "scope": "SOURCE_ROW", "field": "LLM_Predictions",
                    "id": row["id"], "community": row["community"], "raw_output": row["label_raw"],
                    "reason": row["label_status"], "empty_tokens": [], "duplicate_tokens": [],
                    "unexpected_tokens": [],
                })
        for label in LABELS:
            numerator = sum(row["label"] == label for row in eligible)
            sensitivity_rows.append({
                "archive": "classification", "field": "LLM_Predictions", "field_role": "released_label",
                "scope": scope, "category": label, "source_n": source_n,
                "primary_eligible_n": len(eligible), "unknown_union_n": len(unknown),
                "observed_numerator": numerator,
                "primary_proportion": f"{numerator / len(eligible):.12f}" if eligible else "",
                "source_bound_lower": f"{numerator / source_n:.12f}" if source_n else "",
                "source_bound_upper": f"{(numerator + len(unknown)) / source_n:.12f}" if source_n else "",
            })

    parsed_by_field: dict[str, list[tuple[dict, dict]]] = {field: [] for field in FIELDS}
    for row in dimensions:
        community = COMMUNITY_BY_CASEFOLD[str(row["subreddit"]).casefold()]
        normalized = {**row, "community": community}
        for field in FIELDS:
            parsed = parse_dimension(row.get(field))
            parsed_by_field[field].append((normalized, parsed))
            if parsed["status"] == "unknown":
                exception_rows.append({
                    "archive": "dimensions", "scope": "SOURCE_ROW", "field": field,
                    "id": row["id"], "community": community, "raw_output": row.get(field),
                    "reason": parsed["reason"], "empty_tokens": parsed["empty_tokens"],
                    "duplicate_tokens": parsed["duplicate_tokens"],
                    "unexpected_tokens": parsed["unexpected_tokens"],
                })

    field_summary = []
    for field in FIELDS:
        parsed_rows = parsed_by_field[field]
        source_n = len(parsed_rows)
        clean_n = sum(parsed["status"] == "clean" for _, parsed in parsed_rows)
        unknown_n = source_n - clean_n
        prior = day11_qc[field]
        if int(prior["source_n"]) != source_n or int(prior["clean_n"]) != clean_n:
            raise ValueError(f"Day 11 field QC mismatch for {field}")
        if int(prior["missing_n"]) + int(prior["exception_row_n"]) != unknown_n:
            raise ValueError(f"Day 11 unknown-row union mismatch for {field}")
        field_summary.append({
            "field": field, "role": "primary" if field == PRIMARY_FIELD else "sensitivity",
            "source_n": source_n, "clean_eligible_n": clean_n, "unknown_union_n": unknown_n,
            "missing_n": int(prior["missing_n"]), "exception_row_n": int(prior["exception_row_n"]),
        })
        for scope in scopes:
            scoped = parsed_rows if scope == "ALL" else [item for item in parsed_rows if item[0]["community"] == scope]
            eligible = [(row, parsed) for row, parsed in scoped if parsed["status"] == "clean"]
            unknown = [(row, parsed) for row, parsed in scoped if parsed["status"] == "unknown"]
            n_source = len(scoped)
            for dimension in DIMENSIONS:
                numerator = sum(dimension in parsed["tokens"] for _, parsed in eligible)
                sensitivity_rows.append({
                    "archive": "dimensions", "field": field,
                    "field_role": "primary" if field == PRIMARY_FIELD else "sensitivity",
                    "scope": scope, "category": dimension, "source_n": n_source,
                    "primary_eligible_n": len(eligible), "unknown_union_n": len(unknown),
                    "observed_numerator": numerator,
                    "primary_proportion": f"{numerator / len(eligible):.12f}" if eligible else "",
                    "source_bound_lower": f"{numerator / n_source:.12f}" if n_source else "",
                    "source_bound_upper": f"{(numerator + len(unknown)) / n_source:.12f}" if n_source else "",
                })

    for row in sensitivity_rows:
        lower = float(row["source_bound_lower"])
        upper = float(row["source_bound_upper"])
        if not 0 <= lower <= upper <= 1:
            raise ValueError(f"invalid D-021 bound: {row}")
        if int(row["primary_eligible_n"]) + int(row["unknown_union_n"]) != int(row["source_n"]):
            raise ValueError(f"denominator accounting failure: {row}")

    day15_index = {
        (row["archive"], row["scope"], row["category"]): row
        for row in day15_rows
    }
    primary_comparisons = [
        row for row in sensitivity_rows
        if row["field"] in {"LLM_Predictions", PRIMARY_FIELD}
    ]
    for row in primary_comparisons:
        prior = day15_index[(row["archive"], row["scope"], row["category"])]
        if int(prior["count"]) != int(row["observed_numerator"]):
            raise ValueError("Day 17 numerator differs from frozen Day 15 result")
        if int(prior["denominator_n"]) != int(row["primary_eligible_n"]):
            raise ValueError("Day 17 primary denominator differs from frozen Day 15 result")

    sensitivity_path = args.output_dir / "denominator_sensitivity.csv"
    field_summary_path = args.output_dir / "dimension_field_denominator_summary.csv"
    exception_path = args.output_dir / "denominator_exception_ledger.jsonl"
    write_csv(sensitivity_path, list(sensitivity_rows[0]), sensitivity_rows)
    write_csv(field_summary_path, list(field_summary[0]), field_summary)
    with exception_path.open("w", encoding="utf-8") as handle:
        for row in exception_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary_path = args.output_dir / "denominator_sensitivity_summary.md"
    field_lines = "\n".join(
        f"| `{row['field']}` | {row['role']} | {row['source_n']:,} | {row['clean_eligible_n']:,} | {row['unknown_union_n']:,} |"
        for row in field_summary
    )
    summary_path.write_text(
        "# Day 17 denominator sensitivity under D-021\n\n"
        "**Status:** PASS — denominator sensitivity calculated without recoding unknown outputs.\n\n"
        "For every category/dimension and reporting scope, the primary quantity is `x / n_eligible`; the alternate finite-archive identification bound is `[x/N, (x+U)/N]`. These are deterministic sensitivity bounds, not confidence intervals.\n\n"
        "| Dimensions field | Role | Source N | Clean eligible N | Unknown union N |\n"
        "| --- | --- | ---: | ---: | ---: |\n" + field_lines + "\n\n"
        "Missing, empty-token, duplicate-token, and unexpected-token rows are retained as unknown and counted once in `U`. No malformed row is partially encoded, repaired, or treated as dimension absence. Detailed pooled and community-specific results are in `denominator_sensitivity.csv`; row-level provenance is in `denominator_exception_ledger.jsonl`.\n",
        encoding="utf-8",
    )

    reliability_path = args.output_dir / "reliability_sensitivity_status.md"
    reliability_path.write_text(
        "# Day 17 reliability sensitivity\n\n"
        "**Status:** COMPLETE — UNAVAILABLE under the prespecified evidence rule.\n\n"
        "The verified source reports task-1 Fleiss' kappa of 0.42, 77% average agreement, and majority retention of at least 3 of 5 annotators. For the 13 dimensions it reports only overall average agreement of 0.82, with no dimension-level annotation-reliability table.\n\n"
        "Therefore the low-reliability-dimension set is `UNAVAILABLE`. No dimension is designated low reliability; none is omitted, collapsed, reweighted, or relabeled. Model F1, prevalence, and cross-model agreement are not substituted for annotation reliability. The approved primary 13-dimension description is retained, with this unavailable sensitivity recorded as an evidence limitation rather than a numerical robustness result.\n",
        encoding="utf-8",
    )

    freeze_status_path = args.output_dir / "rq1_freeze_status.md"
    freeze_status_path.write_text(
        "# RQ1 freeze status\n\n"
        "**Status:** BLOCKED — not frozen.\n\n"
        "Day 17's canonical dependency requires Day 16 PASS. Day 16 remains `READY — NOT EXECUTED`; no RQ1 table or figure has been produced under D-020. The denominator sensitivity passed and the reliability sensitivity reached its prespecified `UNAVAILABLE` endpoint, but those outcomes do not establish the missing Day 16 prerequisite.\n\n"
        "No RQ1 freeze record was created and no later day was advanced.\n",
        encoding="utf-8",
    )

    checks = {
        "classification_frozen_hash_matches_day14": True,
        "dimensions_raw_hash_matches_day11": True,
        "classification_source_n_is_8520": len(classification) == 8520,
        "classification_unknown_union_n_is_1": sum(row["label_status"] != "canonical" for row in classification) == 1,
        "dimensions_source_n_is_4964": len(dimensions) == 4964,
        "field_qc_matches_day11": True,
        "primary_numerators_and_denominators_match_day15": True,
        "all_bounds_are_ordered_and_in_unit_interval": True,
        "all_denominators_account_for_eligible_plus_unknown": True,
        "no_unknown_output_recoded_as_absence": True,
        "reliability_set_recorded_unavailable": True,
        "day16_pass_present": False,
        "rq1_freeze_created": False,
    }
    qc_path = args.output_dir / "qc_summary.json"
    qc_path.write_text(json.dumps({
        "overall_status": "BLOCKED",
        "denominator_sensitivity_status": "PASS",
        "reliability_sensitivity_status": "COMPLETE_UNAVAILABLE",
        "rq1_freeze_status": "BLOCKED_DAY16_NOT_EXECUTED",
        "checks": checks,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_paths = [
        sensitivity_path, field_summary_path, exception_path, summary_path,
        reliability_path, freeze_status_path, qc_path,
    ]
    manifest_path = args.output_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps({
        "run_id": args.output_dir.name,
        "executed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": "Day 17 denominator sensitivity, evidence-limited reliability disposition, and RQ1 freeze gate review.",
        "locked_rules": ["D-013", "D-017", "D-019", "D-020", "D-021"],
        "inputs": {
            "classification_frozen": {"path": str(args.classification_frozen), "sha256": sha256(args.classification_frozen)},
            "dimensions_raw": {"path": str(args.dimensions_raw), "sha256": sha256(args.dimensions_raw)},
            "day14_record": {"path": str(args.day14_record), "sha256": sha256(args.day14_record)},
            "day11_manifest": {"path": str(args.day11_manifest), "sha256": sha256(args.day11_manifest)},
            "day11_field_qc": {"path": str(args.day11_field_qc), "sha256": sha256(args.day11_field_qc)},
            "day15_source": {"path": str(args.day15_source), "sha256": sha256(args.day15_source)},
        },
        "outputs": {path.name: sha256(path) for path in output_paths},
        "status": {
            "denominator_sensitivity": "PASS",
            "reliability_sensitivity": "COMPLETE_UNAVAILABLE",
            "rq1_freeze": "BLOCKED_DAY16_NOT_EXECUTED",
        },
        "not_executed": ["Day 16 table/figure", "RQ1 freeze", "Day 18 or later work"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
