#!/usr/bin/env python3
"""Recalculate the revised manuscript's descriptive association from frozen counts.

Uses only the already-published 5 x 4 classification count table. This is an
aggregate-to-statistic rerun, NOT a record-level or end-to-end reproduction.
"""
import argparse
import csv
import json
import math
from pathlib import Path

COMMUNITIES = ("ChatGPTCoding", "webdev", "programming", "GitHub", "compsci")
LABELS = ("Trust", "Distrust", "Both", "Neither")
ROOT = Path(__file__).resolve().parents[1]


def calculate(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as handle:
        source = list(csv.DictReader(handle))
    cells = {}
    denominators = {}
    for row in source:
        if row["archive"] != "classification":
            continue
        key = (row["community"], row["category"])
        if key in cells or key[0] not in COMMUNITIES or key[1] not in LABELS:
            raise ValueError(f"unexpected or duplicate classification cell: {key}")
        if row["denominator_type"] != "canonical_label_available":
            raise ValueError(f"wrong denominator rule: {key}")
        count = int(row["count"])
        denominator = int(row["eligible_denominator_n"])
        if count < 0 or denominator <= 0:
            raise ValueError(f"invalid count/denominator: {key}")
        cells[key] = count
        if key[0] in denominators and denominators[key[0]] != denominator:
            raise ValueError(f"inconsistent community denominator: {key[0]}")
        denominators[key[0]] = denominator
    expected = {(c, l) for c in COMMUNITIES for l in LABELS}
    if set(cells) != expected:
        raise ValueError(f"incomplete contingency table: missing {sorted(expected-set(cells))}")
    table = [[cells[c, l] for l in LABELS] for c in COMMUNITIES]
    row_totals = [sum(row) for row in table]
    for c, total in zip(COMMUNITIES, row_totals):
        if total != denominators[c]:
            raise ValueError(f"community count does not match denominator: {c}")
    column_totals = [sum(row[i] for row in table) for i in range(len(LABELS))]
    n = sum(row_totals)
    if n != 8519:
        raise ValueError(f"unexpected frozen eligible N: {n}")
    chi2 = sum((observed - row_totals[i] * column_totals[j] / n) ** 2 /
               (row_totals[i] * column_totals[j] / n)
               for i, row in enumerate(table) for j, observed in enumerate(row))
    v = math.sqrt(chi2 / (n * min(len(COMMUNITIES) - 1, len(LABELS) - 1)))
    contrasts = {c: 100.0 * (cells[c, "Trust"] - cells[c, "Neither"]) / denominators[c]
                 for c in COMMUNITIES}
    contrasts["ALL"] = 100.0 * (column_totals[0] - column_totals[3]) / n
    return {
        "scope": "post hoc descriptive index from previously frozen community-by-label counts",
        "note": "chi_square is used only to derive Cramer's V; no significance test is performed",
        "n": n,
        "chi_square_descriptive": chi2,
        "cramers_v": v,
        "trust_minus_neither_percentage_points": contrasts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results/final_community_table_source.csv")
    parser.add_argument("--output", type=Path, help="optional new report JSON path; refuses overwrite")
    args = parser.parse_args()
    result = calculate(args.input)
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
