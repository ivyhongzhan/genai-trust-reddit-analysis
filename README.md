# GenAI Trust in Technical Reddit Communities — Research Artifacts

This repository contains reproducibility artifacts for Hong Zhan's secondary analysis, *Beyond the Aggregate: Trust and Distrust in Generative AI Across Technical Reddit Communities and Time*. The paper was submitted to PACM HCI / CSCW Rolling Quantitative; acceptance has not been confirmed.

## Study

The analysis describes released trust/distrust classifications and dimensions in five prespecified Reddit communities: `ChatGPTCoding`, `webdev`, `programming`, `GitHub`, and `compsci`. Classification and dimensions are analyzed as separate archives with archive-specific denominators. The analysis uses community and UTC half-year descriptions; it does not make causal, population-prevalence, individual-attitude, or author-occupation claims.

The dimension analysis uses the documented uniform-field replacement estimand `Output_gpt-4.1-2025-04-14_few` with the exact 13-dimension vocabulary and exception rules. This transparent replacement protocol does not reconstruct or validate the original study's mixed, dimension-specific field map. See [`provenance/d013_activation_record.md`](provenance/d013_activation_record.md).

## Current verification status

Existing frozen outputs and manifests report PASS for the RQ1/RQ2 freezes and the Day 28 results inventory. The reported pooled values include classification source N=8,520, canonical-label N=8,519, `Neither` 3,555/8,519 (41.7%), `Trust` 3,408/8,519 (40.0%), and dimensions `Competence` 3,506/4,964 (70.6%). Community-specific `Trust` is 43.1% in `ChatGPTCoding` and 46.2% in `programming`.

This repository documents that a complete raw-data-to-paper rerun was not established and does **not** claim a complete raw-data-to-paper rerun. The extracted frozen input JSON files were absent from the inspected project tree, and the file named `tacl_data.zip` was an HTML response rather than a ZIP. Several downstream manifests explicitly document reference-only verification or no recalculation. The source-chain and submission identity limits are recorded in [`provenance/source_chain.json`](provenance/source_chain.json).

## Contents

- `scripts/`: preserved Day 15 and Day 18 Python analysis scripts, adjusted only to remove one record ID from public QC output.
- `results/`: aggregate, community, temporal, and pooled-versus-stratified source tables and reports copied from frozen artifacts.
- `figures/`: frozen paper-facing figures copied without regeneration.
- `provenance/`: sanitized freeze records, scientific protocol, source chain, and submission source manifest.
- `tests/`: deterministic smoke and scientific consistency checks over packaged aggregate artifacts.

No raw Reddit records, row-level analytic JSONL, author fields, usernames, post text, post titles, or record IDs are included. The source project is preserved separately and was not modified.

## Verify this package

Requires Python 3.10 or later; the standard-library checks have no third-party dependencies.

```bash
python3 scripts/verify_package.py
python3 -m unittest discover -s tests -v
```

The copied Day 15 and Day 18 scripts are the authentic execution code preserved in the source project. Full raw-input execution requires the exact frozen inputs and upstream manifests documented in the source project; their absence is a current limitation. Do not substitute or reconstruct inputs.

## Reproduce the manuscript build

The candidate anonymous LaTeX source ZIP is documented in the source project. The exact uploaded PDF could not be established: the bundle SHA manifest records a different hash from the current local build, so no PDF is included here. See [`provenance/submission-source-manifest.sha256`](provenance/submission-source-manifest.sha256) and [`provenance/source_chain.json`](provenance/source_chain.json).

## License

No license is declared. Rights and licensing conditions for the underlying dataset and derived materials have not been established for redistribution in this repository.
