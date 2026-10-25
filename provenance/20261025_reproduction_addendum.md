# Reproduction addendum, 2026-10-25

This addendum supplements but does not overwrite historical source and freeze records. Some older records accurately describe the files visible to an earlier repository inspection and should not be read as the latest local research project inventory.

## A01 local recovery

The classification and dimensions extracted archives, Day 11 dimension encoding input, and both analytic Day 14 frozen JSONL inputs were located in the preserved local research project. All five SHA256 digests matched their authoritative records. The 14 KB file named `tacl_data.zip` was a saved HTML 404 response and was not the source of those verified inputs.

## A02 reruns

Day 15: four output files exactly matched. Day 16: numerical tables, PNG and TIFF matched; PDF and SVG hashes differed. Day 17: seven sensitivity files exactly matched, while original downstream QC retained its previous upstream `BLOCKED` disposition. Day 18: analytical outputs exactly matched; an expected run identifier changed in one provenance record. Day 20 and later were not independently rerun.

## A03 figure audit

The Day 16 PDF files were identical after normalizing only CreationDate. SVG documents matched after normalizing export dates and generated internal identifiers. Rendered PDF pixels were identical at the tested resolution; the text size and collision audits passed. This is visual and scientific equivalence, not raw byte identity of vector files.

## Scope

These are reported local source project audit results. Raw and row level inputs, the full output directory and the exact ScholarOne uploaded manuscript PDF are not in this GitHub repository. A complete independent raw data to manuscript rerun has not been established.

## Historical document interpretation

The earlier `provenance/source_chain.json` records what was available in that particular inspection, not a permanent claim that the later recovered Day 14 inputs do not exist. It is deliberately retained unchanged as historical provenance.
