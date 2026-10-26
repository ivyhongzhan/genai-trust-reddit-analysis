# Reproduction and Verification

This repository provides preserved analysis scripts, frozen aggregate outputs, research figures, provenance documentation, and automated verification tools.

## Quick Verification

Run the following commands from the repository root.

**1. Verify the research artifacts**

```bash
python3 scripts/verify_package.py
```

**2. Run the included tests**

```bash
python3 -m unittest discover -s tests -v
```

The verifier checks:

- SHA-256 integrity of 12 frozen files.
- Selected classification and dimension counts.
- Reported proportions and denominator consistency.
- Temporal coverage and reporting boundaries.

The included verification scripts use Python's standard library.

## Analysis Scripts

| Script | Purpose |
|---|---|
| `scripts/run_day15_rq1_counts.py` | Descriptive classification and dimension summaries |
| `scripts/run_day18_rq2_community.py` | Community-stratified analysis |
| `scripts/verify_package.py` | Frozen artifact integrity and numerical verification |

The preserved analysis scripts require corresponding verified frozen inputs and configuration records. These record-level inputs are not distributed in this repository.

## Research Outputs

The repository includes:

- `results/` — frozen aggregate statistics and supporting analytical tables.
- `figures/` — research figures and temporal visualizations.
- `provenance/` — methodological decisions, data freezes, denominator rules, and verification records.
- `tests/` — automated verification tests.

## Reproduction Scope

The distributed package supports verification of selected numerical results, preserved analytical outputs, and file integrity.

Separate local verification established consistency across major analytical stages, including descriptive tables and research visualizations.

A complete independent rerun from the original record-level inputs to the final manuscript requires additional source files and processing steps not distributed here.

Detailed verification evidence, including the scope of completed and incomplete reruns, is retained in the [reproduction addendum](provenance/20261025_reproduction_addendum.md).

Passing GitHub Actions indicates successful execution of the included verification tests; it does not establish complete end-to-end reproduction.

## Release Archive Integrity

A separate, version-controlled builder prepares a **release candidate** from the public
research repository without re-running or changing frozen scientific results:

```bash
python3 scripts/build_zenodo_release.py
python3 scripts/build_zenodo_release.py --verify genai-trust-reddit-analysis_release-candidate.zip
```

The candidate includes `ARCHIVE_MANIFEST.json`, which records the GitHub source
commit and SHA-256 checksum and byte size of every included file. Its embedded
`CITATION.cff` uses the all-version (concept) DOI until a new version-specific
DOI is assigned by Zenodo; no publication date or version DOI is invented.
Only the documented repository files are packaged, including explicit file-level
license declarations; raw Reddit records are not included in this distribution.

Archive-wide integrity verification is **not** equivalent to independent
reproduction of the research from record-level source data. The existing
12 frozen scientific-file hash checks remain separate.

## Research Archive

The software and associated materials are archived on Zenodo.

**[Research Artifacts — Version v2](https://doi.org/10.5281/zenodo.23655847)**

[All-version DOI](https://doi.org/10.5281/zenodo.23653961)
