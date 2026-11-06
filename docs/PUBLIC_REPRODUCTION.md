# Public reproduction: scope and instructions

This workflow rebuilds the main numerical results and three principal figure layouts from two public Zenodo source archives. It uses Python packages without new LLM or Reddit API calls.

The inputs contain **record-level data**. The workflow creates private JSON and JSONL intermediates outside the checkout; it does not require private manuscript sources. It checks specified outputs rather than reproducing the complete manuscript or every historical analysis. Exact figure pixels depend on the fonts, renderer, and platform.

## Inputs and environment

Obtain the two original files from [the source dataset, Zenodo record 20331918](https://doi.org/10.5281/zenodo.20331918). Keep them in a **private directory outside the checkout**:

```sh
mkdir -p /path/to/private-zips
curl --fail --location -o /path/to/private-zips/Trust_Classification_json.zip 'https://zenodo.org/api/records/20331918/files/Trust_Classification_json.zip/content'
curl --fail --location -o /path/to/private-zips/Dimensions_of_Trust_json.zip 'https://zenodo.org/api/records/20331918/files/Dimensions_of_Trust_json.zip/content'
```

The workflow checks SHA-256 before extraction: classification
`270cea2a422d2930390a368f0049f34bf9566799583d218f6374ee84723458a7`;
dimensions `0bc2664683b0987c054be3bb172bf4e14a86c9bd8e4a7bf3e325e653cc057ffb`.
It also checks the JSON members, source row counts and all six historical Day 14
artifact hashes. A changed archive fails; it is never silently accepted.

Create the analysis environment from `environment.yml` with conda, or use Python
3.9 in a new virtual environment and install the observed versions:

```sh
python3.9 -m venv /path/to/new-venv
/path/to/new-venv/bin/python -m pip install numpy==2.0.2 matplotlib==3.9.4 PyMuPDF==1.26.5 Pillow==11.3.0
/path/to/new-venv/bin/python scripts/reproduce_public.py \
  --zip-dir /path/to/private-zips \
  --output-dir /path/to/new-private-run
```

The output must not already exist, be inside the checkout, or overlap the ZIP
directory. It is created with owner-only permissions. **It contains source JSON,
record-level JSONL and exception ledgers with identifiers and released fields. Do
not commit, upload, or publish the complete run.** Consult the original dataset
license and ethics terms before accessing or sharing the source. Logs and manifests
can also contain local paths; review and redact them before sharing.

## Checks and outputs

The new Day 11 encoding and all six Day 14 artifact hashes are compared to the
historical freeze. Newly computed Day 15, Day 18, Day 20 and RQ3 tables are
compared with packaged aggregate targets and historical aggregate hashes.
The revised-manuscript audit fixture independently checks 20 recorded fraction
occurrences against their named generated cells. The 85 community table cells,
three reported temporal ranges and the revised descriptive association are also
checked. The fixture records the scope of a previous manuscript audit; it does
not distribute or verify the complete manuscript or its external citations.

The new Day 18 rerun is checked as a computational prerequisite to the Day 20
rerun. The original historical Day 19 PASS gate is **not** reissued. Day 17's
numerical sensitivity table is compared to its historical hash, while its
original overall gate remains **BLOCKED** and its reliability disposition remains
`COMPLETE_UNAVAILABLE`. No new research freeze is claimed.

`paper/figure1.pdf` is the new 320 dpi-embedded export. The frozen historical
200 dpi Figure 1 is regenerated separately for comparison and is not replaced.
The new export is checked for actual embedded-image resolution, panel alignment,
source preflight, PDF text size, and rendered collisions. Figures 2–3 are generated
with the revised manuscript layout. Historical layouts for all three figures are
compared with the earlier revised-manuscript audit via hashes of their 144 dpi
pixel renders. Exact pixels depend on fonts, renderer and platform: a mismatch
is reported as FAIL, not automatically evidence that data differ. The bundled
QA tools and their upstream license are in `vendor/nature_figure_qa/`.

`report.json` contains explicit checks and the final PASS/FAIL; `commands.json`,
`logs/`, `environment.json`, `input_inventory.json` and `output_inventory.json`
retain execution and hash evidence. Any command or comparison failure yields a
nonzero exit and leaves completed evidence in place. A PASS applies only to the
listed checks and environment, not the whole manuscript or all research gates.
The [2026-11-05 public acceptance audit](PUBLIC_REPRODUCTION_AUDIT_20261105.md) records the clean-checkout run and its limits.

The older private-input workflow and its historical FAIL audit remain documented
in [END_TO_END_LOCAL_RUN.md](END_TO_END_LOCAL_RUN.md) and
[REPRODUCTION_AUDIT_20261105.md](REPRODUCTION_AUDIT_20261105.md).

The Day 24 original supporting-figure rendering code remains unavailable; its
numerical source tables are regenerated and checked. The exact uploaded submission
PDF, full manuscript prose, external-source claims, annotation reliability,
construct validity and the original mixed-field estimand are not established by
this workflow. Public CI verifies frozen aggregate files and unit tests; it does
not download or process record-level source data.
