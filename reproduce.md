# Reproduction and verification

## Reproduce the packaged artifact checks

Run these commands from the repository root:

```bash
python3 scripts/verify_package.py
python3 -m unittest discover -s tests -v
```

The verifier checks 12 frozen file hashes, selected numerator and denominator values, community percentages, temporal coverage, and the presence of an accurate disclosure of reproduction limits. This operation verifies packaged outputs; it does **not** execute the source study from its raw inputs.

## Confirmed local rerun, October 25, 2026

Separate audits in the preserved local research project established the following:

| Source stage | Reproduction status |
| --- | --- |
| Day 14 | Three direct frozen inputs and two analytic JSONL files present with matching SHA-256 |
| Day 15 | All four output files match exactly |
| Day 16 | All numerical tables and raster figures match; PDF/SVG normalized content and rendered pixels are identical, despite nondeterministic timestamp and SVG IDs |
| Day 17 | All seven output hashes match, but historical QC remains `BLOCKED` |
| Day 18 | Seven of eight output files match exactly; the only difference is a run specific provenance `run_id` |
| Day 20 | Not rerun because the original script writes to an occupied frozen output directory |

The Day 16 audit found no scientific difference. Original frozen materials were not overwritten. A complete raw-data-to-paper rerun was not established.

## Data availability and boundaries

The three direct Day 14 inputs and two frozen analytical JSONL inputs have been verified **in the local source project**, but they are not included in this GitHub repository. The original `tacl_data.zip` file in that project was an HTML 404 response, not the authoritative frozen data. See [data availability](data/README.md).

The preserved Day 15 and Day 18 scripts require verified frozen JSONL files and freeze records at user supplied paths. Do not substitute unrelated extracts or introduce the later author supplied Mixtral data into this frozen analysis.

Several subsequent output manifests document projected or reference only checks, not a newly executed analysis. Missing generating code or input files must remain marked unverified rather than inferred from the existing outputs.

## Submitted manuscript identity

The source package records a SHA-256 for a candidate submission PDF, but the exact ScholarOne uploaded file has not been independently established. This repository does not claim that its candidate PDF is the submitted file, and does not include a manuscript PDF.
