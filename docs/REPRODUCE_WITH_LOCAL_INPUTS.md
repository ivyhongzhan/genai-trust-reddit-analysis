# Record-level reproduction: verified subset and remaining gaps

## What this adds

This branch provides two **separate** reproducibility routes:

1. **Day 14 record-level inputs → RQ1 and community-level RQ2.** The wrapper executes the preserved Day 15 and Day 18 scripts and compares every row and column of three regenerated CSV outputs to the existing frozen snapshots; it also recalculates the revised-manuscript descriptive association from newly regenerated community counts and compares it against the frozen count-based reference. It does not use the committed aggregate results as analysis input.
2. **Frozen community counts → revised-manuscript descriptive association.** A standalone Python script recalculates Cramer's V, the descriptive chi-square quantity, and Trust-minus-Neither percentage-point contrasts. This step starts from published aggregate counts, not record-level data.

All calculations remain archive-separated. No label recoding, source data edits, new sampling, inferential testing, cross-archive join, or changes to the reported manuscript numbers are introduced.

## Local-input rerun (not executable in public CI)

You need the two original Day 14 JSONL files in the preserved local research project. They are not included in this public repository.

Recorded SHA-256 digests:

- classification_analytic_frozen.jsonl: 890ace6d2bdc36961bbc5e24bc1342a4f98a8e9c21cd1a1ac730276cac9de31d (8,520 rows).
- dimensions_analytic_frozen.jsonl: e898e3468f76ecae112181c1065c67d64a101a5e9048493f001e3bb16c51fead (4,964 rows).

Run in the root directory of this repository, replacing the paths below with the existing local files:

~~~sh
python3 scripts/reproduce_frozen_inputs.py \
  --classification "/path/to/classification_analytic_frozen.jsonl" \
  --dimensions "/path/to/dimensions_analytic_frozen.jsonl" \
  --output-dir "/path/to/new-reproduction-run"
~~~

The script refuses to overwrite its output folder and rejects incorrect input hashes before running any analysis. It invokes the preserved scripts, compares the new Day 15 and Day 18 numeric CSV outputs against the committed snapshots, and writes:

- new-reproduction-run/day15/
- new-reproduction-run/day18/
- new-reproduction-run/reproduction_report.json

The report includes the descriptive association recomputed from Day 18 output and identifies any cell mismatch and does not claim end-to-end raw-data-to-paper reproduction. Because frozen inputs are not present on GitHub, a successful public GitHub Actions run cannot establish that these record-level commands have been run.

## Reproduce revised-manuscript descriptive association

~~~sh
python3 scripts/reproduce_posthoc_association.py
~~~

From results/final_community_table_source.csv, the expected descriptive quantities are:

- N = 8,519.
- Descriptive chi-square quantity: 137.5163864065677 (manuscript: 137.516).
- Cramer's V: 0.07335374468450037 (manuscript: 0.073).

No p-value, test of significance, confidence interval, or sampling inference is computed.

## CI and interpretation

~~~sh
python3 -m unittest discover -s tests -v
python3 scripts/verify_package.py
~~~

The unit tests check the aggregate association calculation and comparison behavior, including deliberate malformed data. The existing CI checks frozen hashes and selected facts; it does not rerun research analyses on the original record-level inputs.

## What remains to establish complete reproduction

- Original released Zenodo archive → Day 14 filtered and parsed analytical JSONL, using the historically locked five-community eligibility, time, label, and dimension rules.
- Independent rerun and numerical comparison of Day 20 temporal tables, RQ3, revised-manuscript association derived from regenerated counts, and all paper figures.
- Reproduction report with environment, provenance, exact source inputs/hashes, command log, output checks and explicit PASS/FAIL per paper result.

The original project reports that Day 14 frozen inputs existed locally and passed hash validation; no record-level data are added to this repository. There is currently no independently verified end-to-end rerun. Do not relabel GitHub Actions passing checks as proof of that stronger claim.
