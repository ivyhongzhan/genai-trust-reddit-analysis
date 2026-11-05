#!/usr/bin/env python3
"""Run the locked Day 11 classification-denominator and dimension-encoding QC."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


COMMUNITIES = ["ChatGPTCoding", "webdev", "programming", "GitHub", "compsci"]
COMMUNITY_BY_CASEFOLD = {community.casefold(): community for community in COMMUNITIES}
CANONICAL_LABELS = ["Trust", "Distrust", "Both", "Neither"]
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_dimension(raw: object) -> tuple[str, list[str], list[str], list[str], bool]:
    if raw is None or not str(raw).strip():
        return "missing", [], [], [], False
    tokens = [token.strip() for token in str(raw).split(",")]
    empties = [token for token in tokens if not token]
    unexpected = [token for token in tokens if token and token not in DIMENSIONS]
    duplicates = [token for token, n in Counter(tokens).items() if token and n > 1]
    status = "clean" if not empties and not unexpected and not duplicates else "exception"
    return status, tokens, empties, unexpected, bool(duplicates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    classification = json.loads(args.classification.read_text(encoding="utf-8"))
    dimensions = json.loads(args.dimensions.read_text(encoding="utf-8"))
    selected_classification = [r for r in classification if str(r.get("subreddit", "")).casefold() in COMMUNITY_BY_CASEFOLD]
    selected_dimensions = [r for r in dimensions if str(r.get("subreddit", "")).casefold() in COMMUNITY_BY_CASEFOLD]

    class_counts: dict[str, Counter] = defaultdict(Counter)
    class_source: Counter = Counter()
    class_available: Counter = Counter()
    class_exceptions: list[dict] = []
    for record in selected_classification:
        community = COMMUNITY_BY_CASEFOLD[str(record["subreddit"]).casefold()]
        class_source[community] += 1
        raw = record.get("LLM_Predictions")
        value = "" if raw is None else str(raw).strip()
        if value in CANONICAL_LABELS:
            class_counts[community][value] += 1
            class_available[community] += 1
        else:
            reason = "missing" if not value else "noncanonical"
            class_exceptions.append({"id": record.get("id", ""), "community": community, "reason": reason, "raw_value": value})

    denominator_rows = []
    for community in ["ALL", *COMMUNITIES]:
        source_n = len(selected_classification) if community == "ALL" else class_source[community]
        available_n = sum(class_available.values()) if community == "ALL" else class_available[community]
        denominator_rows.append({
            "community": community,
            "source_denominator": source_n,
            "label_available_denominator": available_n,
            "missing_or_noncanonical_n": source_n - available_n,
        })

    label_rows = []
    for community in ["ALL", *COMMUNITIES]:
        counts = sum(class_counts.values(), Counter()) if community == "ALL" else class_counts[community]
        available_n = sum(counts.values())
        for label in CANONICAL_LABELS:
            count = counts[label]
            label_rows.append({
                "community": community,
                "label": label,
                "n": count,
                "label_available_denominator": available_n,
                "share": f"{count / available_n:.12f}" if available_n else "",
            })

    all_fields = [PRIMARY_FIELD, *SENSITIVITY_FIELDS]
    field_qc_rows = []
    primary_encoding_path = args.output_dir / "primary_dimension_encoding.jsonl"
    with primary_encoding_path.open("w", encoding="utf-8") as encoding_handle:
        for field in all_fields:
            missing = exception_rows = empty_token_rows = unexpected_token_rows = duplicate_token_rows = 0
            for record in selected_dimensions:
                status, tokens, empties, unexpected, has_duplicate = parse_dimension(record.get(field))
                if status == "missing":
                    missing += 1
                elif status == "exception":
                    exception_rows += 1
                if empties:
                    empty_token_rows += 1
                if unexpected:
                    unexpected_token_rows += 1
                if has_duplicate:
                    duplicate_token_rows += 1
                if field == PRIMARY_FIELD:
                    clean = status == "clean"
                    encoded = {
                        "id": record.get("id"),
                        "subreddit": record.get("subreddit"),
                        "field": PRIMARY_FIELD,
                        "raw_output": record.get(field),
                        "encoding_status": status,
                        **{dimension: (1 if clean and dimension in tokens else 0) if clean else None for dimension in DIMENSIONS},
                    }
                    encoding_handle.write(json.dumps(encoded, ensure_ascii=False, sort_keys=True) + "\n")
            field_qc_rows.append({
                "field": field,
                "role": "primary" if field == PRIMARY_FIELD else "sensitivity",
                "source_n": len(selected_dimensions),
                "present_n": len(selected_dimensions) - missing,
                "missing_n": missing,
                "clean_n": len(selected_dimensions) - missing - exception_rows,
                "exception_row_n": exception_rows,
                "empty_token_row_n": empty_token_rows,
                "unexpected_token_row_n": unexpected_token_rows,
                "duplicate_token_row_n": duplicate_token_rows,
            })

    write_csv(args.output_dir / "classification_denominators.csv", list(denominator_rows[0]), denominator_rows)
    write_csv(args.output_dir / "classification_label_counts.csv", list(label_rows[0]), label_rows)
    write_csv(args.output_dir / "classification_exceptions.csv", ["id", "community", "reason", "raw_value"], class_exceptions)
    write_csv(args.output_dir / "dimension_field_qc.csv", list(field_qc_rows[0]), field_qc_rows)

    primary_qc = next(row for row in field_qc_rows if row["field"] == PRIMARY_FIELD)
    checks = {
        "classification_source_n_is_8520": len(selected_classification) == 8520,
        "classification_available_n_is_8519": sum(class_available.values()) == 8519,
        "classification_exception_is_historical_missing_record": (sha256(args.classification) == "a788f72a49fb6205d9fd06cd32e8c3397dbd1c597556b62af329d3ef2b808336" and len(class_exceptions) == 1 and class_exceptions[0]["reason"] == "missing"),
        "classification_counts_sum_to_available": sum(sum(counter.values()) for counter in class_counts.values()) == 8519,
        "classification_community_source_counts_match_day2": [class_source[c] for c in COMMUNITIES] == [5333, 2011, 513, 378, 285],
        "classification_community_available_counts_sum": sum(class_available[c] for c in COMMUNITIES) == 8519,
        "dimensions_source_n_is_4964": len(selected_dimensions) == 4964,
        "primary_field_all_rows_clean": primary_qc["clean_n"] == 4964 and primary_qc["missing_n"] == 0 and primary_qc["exception_row_n"] == 0,
        "primary_encoding_has_4964_rows": sum(1 for _ in primary_encoding_path.open(encoding="utf-8")) == 4964,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    qc_summary = {"status": status, "checks": checks, "primary_field_qc": primary_qc}
    (args.output_dir / "qc_summary.json").write_text(json.dumps(qc_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_names = [
        "classification_denominators.csv", "classification_label_counts.csv",
        "classification_exceptions.csv", "dimension_field_qc.csv",
        "primary_dimension_encoding.jsonl", "qc_summary.json",
    ]
    manifest = {
        "run_id": args.output_dir.name,
        "purpose": "Day 11 mechanical encoding and denominator QC; no archive join, temporal analysis, model, figure, or RQ interpretation.",
        "inputs": {
            "classification": {"path": str(args.classification), "sha256": sha256(args.classification), "source_records": len(classification)},
            "dimensions": {"path": str(args.dimensions), "sha256": sha256(args.dimensions), "source_records": len(dimensions)},
        },
        "communities": COMMUNITIES,
        "classification_rule": "Retain N=8,520 in the source funnel; compute category shares over canonical-label N=8,519; show missing/noncanonical separately.",
        "primary_dimension_field": PRIMARY_FIELD,
        "sensitivity_fields": SENSITIVITY_FIELDS,
        "dimension_parser": "Preserve raw string; split present nonblank values on literal commas; trim token edges; exact-match the 13-token vocabulary; retain exceptions.",
        "outputs": {name: sha256(args.output_dir / name) for name in output_names},
        "qc_status": status,
    }
    (args.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
