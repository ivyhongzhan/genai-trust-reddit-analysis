# Numerical reproduction audit — 2026-11-05

Executed code commit: `6559a14`. Baseline: `e7f841ff4d7b3d05fcdcab99cfc439ef58fac7bb`.

- Overall strict report: **FAIL**. Numerical reproduction: **PASS**. Main-figure rendering: **PASS**.
- Rebuilt Day 11/14 from hash-matched cached public release ZIPs. Classification source JSON: 230,575 rows; dimensions: 135,061. Rebuilt frozen analytical JSONL: 8,520 and 4,964 rows, with exact historical hashes.
- Recalculated RQ1, community/temporal RQ2, all RQ3 numerical sources, the manuscript's 85-cell table, temporal ranges, composition weight and previously reported post-hoc descriptive association. Nineteen CSV comparison records were byte-identical. Public record-ID redactions were verified separately from private originals.
- All three revised manuscript main figures have identical pixels at 144 dpi and identical decoded PDF objects excluding CreationDate. Their numerical inputs were newly generated, not copied from frozen output tables.
- Forty-five of 46 report checks passed. The historical Figure 1 vector export embeds heatmaps at 200 dpi; the current >=300 dpi source preflight reports FAIL. This FAIL remains unchanged. PNG is 300 dpi and TIFF 600 dpi; they do not override the failed check.
- Nine unit tests and the original 12 frozen-file integrity checks passed. Complete branch diff formatting checks passed.

The final command returned exit code 1. This is not a claim that every research gate passed or every historical artifact was reproduced. Day 17's original hardcoded final gate remains BLOCKED; its sensitivity values match. The original Day 24 supporting-figure rendering code is unavailable, although every supporting numerical source is regenerated. The exact uploaded submission PDF is not established, and no fresh public download was performed. No new sampling, LLM calls, Reddit collection, raw-record redistribution, merge or publication occurred.

Use `docs/END_TO_END_LOCAL_RUN.md` to run the workflow with privately held inputs. Execution JSON, commands, environment and file hash manifests were retained locally and supplied as a record-free audit bundle. Public CI still does not run this record-level workflow.
