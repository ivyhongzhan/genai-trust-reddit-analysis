# Local end-to-end numerical reproduction

This route rebuilds the paper's primary numerical results from the two cached
public release ZIPs. Record-level files are never committed or redistributed.
The branch's existing frozen-input wrapper remains available unchanged in scope.
The new workflow does not download, resample, relabel, hydrate Reddit posts, or
change the paper's method, frozen decisions, original inputs, or reported values.

## Prerequisites

Use the observed runtime recorded with the execution evidence: Python 3.9.6,
matplotlib 3.9.4, NumPy 2.0.2, PyMuPDF 1.26.5 and Pillow 11.3.0. The package
`environment.yml` records the original analysis subset, not the entire new audit
environment; `environment.json` from each audit inventories the actual runtime.

Supply the preserved research project, the exact manuscript source directory,
and the original nature-figure QA scripts directory. The latter must contain
`audit_panel_alignment.py`, `validate_figure.py`, `audit_pdf_text.py`, and
`audit_figure_collisions.py`. All QA source hashes and a local source snapshot
are saved in the run. That dependency is not redistributed in this repository.

The manuscript directory must include main/content TeX, `tables/table1.tex`,
and `figures/figure1.pdf` through `figure3.pdf`. The dated audit identifies the
specific local revised manuscript used; this does not establish which PDF was
uploaded to a submission service or the paper's publication status.

## Execute

```sh
python3 scripts/reproduce_end_to_end.py \
  --research-root /path/to/preserved/research-project \
  --manuscript-root /path/to/revised-manuscript \
  --figure-qa-scripts /path/to/nature-figure/scripts \
  --output-dir /path/to/new-private-run
```

The output directory must be new and outside the research project, manuscript,
and repository's frozen results/provenance/figures directories. The run directory
is owner-only. It contains raw JSON and record-level intermediate JSONL: **never
commit or publish the full run directory**. A public audit bundle must explicitly
exclude `raw/`, `rebuilt_day14/`, `day11/primary_dimension_encoding.jsonl`, and
all other record-level or exception-record files.

## Computation and comparison

1. Verify the 12 packaged frozen-artifact hashes. Verify and execute the existing
   branch wrapper on the original Day 14 JSONL (Day 15/18 plus revised association).
2. Verify each public ZIP against the historical download manifest; extract only
   its exact JSON member into the new run and verify original JSON hashes/rows.
3. Execute the preserved Day 11 parser. Match its 4,964-row encoding hash.
4. Execute Day 14, then match both JSONL and all six listed artifact hashes.
   Its new version record has new input paths and run ID; it is not a new freeze.
5. Recalculate Day 15/18 from the rebuilt JSONL using the authoritative freeze
   record as hash authority. Recalculate Day 17 sensitivity and Day 20 temporal
   summaries. The Day 20 historical Day 19 PASS files are provenance anchors
   only; no old community/temporal values supply the new counts.
6. Rebuild Day 22 projections, Day 23 same-archive pairings and Day 24 table/figure
   sources. Compare every CSV column, keyed row and status against frozen targets.
   Targets are used only after the new counts are generated.
7. Regenerate the manuscript's 85-cell table including revised percentages,
   Figure 1 and the revised-layout Figures 2–3. Recompute Cramér's V, the
   descriptive chi-square quantity, contrasts, temporal ranges and composition
   weight; compare the actual paper's fraction/percentage occurrences and
   explicit contextual claims. These checks are not an audit of cited studies.
8. Compare PDFs at 144 dpi and compare decoded PDF objects, excluding only the
   recorded creation date. Preserve PDF metadata, hashes, alignment, source
   preflight, text-size and collision audit evidence.

All exact counts and string/status fields must match. Proportion fields in the
original wrapper use absolute tolerance 1e-12 with finite numbers only; blank
unavailable values must remain blank and differ from 0. Duplicate keys/headers
and malformed CSV rows are errors. The execution also records byte equality;
in the dated successful numerical run, every compared CSV was byte-identical.

## Status and known historical issues

The JSON report separates overall `status`, `numerical_status` and
`figure_render_status`. Nonzero QA return codes remain FAIL; they are never
converted into PASS because the numerical reproduction succeeds. A failure
keeps command logs and all completed artifacts. Output directories are never
reused; failed attempts remain evidence.

The current Day 16 source differs from its historical rendered canvas. Frozen
alignment QA establishes 504 × 538.56 pt (7 × 7.48 in). Historical PDF image
objects establish 200 dpi heatmap embedding. The preserved copy in this branch
explicitly restores that display contract, without altering any data values.
The modern source lint flags that historical 200 dpi vector-export argument
against its 300 dpi raster rule. This FAIL is retained even though PNG is
300 dpi, TIFF is 600 dpi, and the recreated PDF is identical in decoded page
content. No QC threshold is weakened and no metadata is forged.

The historical Day 17 script hardcodes missing Day 16/freeze gates. Its numerical
sensitivity artifact can reproduce exactly while its original final gate remains
BLOCKED. This workflow does not issue or overwrite a scientific freeze.

The original supporting Day 24 figure-rendering code is still unavailable;
all its numerical sources are regenerated. Those two supporting figures are
not among the revised manuscript's three main figures. The report does not
claim that every historical project artifact, manuscript prose, source-study
estimand or submission PDF is reproduced. Public CI lacks record-level inputs
and therefore cannot establish this local reproduction.
