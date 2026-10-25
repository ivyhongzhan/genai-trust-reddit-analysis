# Data availability and provenance

The underlying classification and dimensions archives come from the source study's [Zenodo dataset](https://doi.org/10.5281/zenodo.20331918). Check the current record's license and reuse terms before downloading or redistributing files.

## Verified Day 14 inputs

A targeted local audit on October 25, 2026 found all three directly required Day 14 inputs and the two frozen analytical JSONL files. All five SHA-256 digests matched their recorded values in the authoritative Day 14 version record. The source archive contained 8,520 classification records and 4,964 dimension records. The local research project retains those exact inputs and source paths.

**These record level inputs are not redistributed in this repository.** The repository contains derived aggregate tables and a verifier.

The separate file named `tacl_data.zip` was a Zenodo 404 HTML response saved with a ZIP filename. This failed download is not evidence that the verified frozen inputs were missing.

An author supplied Mixtral CSV was outside the Paper 1 frozen estimand; it must not be substituted into the source data or treated as having been used by the analysis. Its provenance is maintained separately.

For the tests that can be run directly from this GitHub repository, see [the reproduction instructions](../reproduce.md).
