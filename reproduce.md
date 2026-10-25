# Reproduction and verification

## What is verified here

The package verification script checks its file hashes, presence of frozen aggregate tables and figures, expected headline counts/proportions, separate archive denominators, and temporal comparison boundaries. It does not rerun the research analysis from raw inputs.

```bash
python3 scripts/verify_package.py
python3 -m unittest discover -s tests -v
```

## Full raw-input rerun status

The original project records raw-input SHA-256 values and Day 14 frozen-input SHA-256 values in the version record. The extracted JSONL inputs referenced by that freeze were absent from the inspected project checkout. The available `data/raw/tacl_data.zip` is an HTML response, not a usable archive. Therefore the preserved scripts cannot be run end-to-end from the artifacts available in this package.

The original project does preserve the Day 15 count script and Day 18 community script. Other downstream outputs include frozen data and manifests, but not all generating scripts; the Day 20 preserved script references a temporary source path in its QA workflow, and Days 22–27 were documented as frozen-value projections or evidence inventories. No missing computation is represented as reproduced here.

## Input recovery needed for full rerun

Recover the exact released archives from the cited Zenodo record and independently verify their SHA-256 values against the source project's freeze record before using them. Restore the extracted Day 14 files from their authoritative source only if their hashes match the recorded values. Then use the preserved scripts with their recorded inputs and outputs, in a clean copy, following the frozen decisions and archive-specific denominators. Do not join the archives or alter fields, exclusions, parser behavior, or temporal boundaries.
