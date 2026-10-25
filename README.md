# Beyond the Aggregate

**Trust and Distrust in Generative AI Across Technical Reddit Communities and Time**

Hong Zhan | Research Artifacts | 2026

*Manuscript submitted to PACM HCI (CSCW Rolling Quantitative). Not yet accepted or published.*

[![Research artifact verification](https://github.com/ivyhongzhan/genai-trust-reddit-analysis/actions/workflows/verify.yml/badge.svg)](https://github.com/ivyhongzhan/genai-trust-reddit-analysis/actions/workflows/verify.yml)

[Research Figure](figures/rq1_figure.pdf) · [Reproduction Guide](reproduce.md) · [Original Dataset](https://doi.org/10.5281/zenodo.20331918)

## TL;DR

**Question.** What do pooled statistics leave unresolved about trust and distrust in generative AI across different online communities?

**Approach.** I conducted a descriptive secondary analysis of released research data from five technical Reddit communities. Classification and dimension archives were analyzed separately, with community and temporal strata and explicit measurement boundaries.

**Finding.** *Neither* was the most frequent pooled classification (41.7%), whereas *Trust* was the most frequent classification in ChatGPTCoding (43.1%) and programming (46.2%). Pooled and community specific summaries describe different aspects of the same sampled discourse.

### Main research figure

![Figure 1. Pooled and community specific trust and distrust classification labels and dimension indicators across five sampled technical Reddit communities.](figures/rq1_figure.png)

**Figure 1.** Classification labels and primary field dimensions across five technical Reddit communities. Classification and dimensions come from separate archives with different denominators. [View the original vector figure (PDF)](figures/rq1_figure.pdf) · [Lossless WebP](figures/rq1_figure.webp).

## Quick Start

The following steps verify the **packaged frozen artifacts**. They do not constitute a full raw data to manuscript rerun.

**1. Clone with authorized GitHub access.** This repository is private.

```bash
git clone https://github.com/ivyhongzhan/genai-trust-reddit-analysis.git
cd genai-trust-reddit-analysis
```

**2. Verify frozen outputs.** Requires Python 3.10 or later; the package verifier uses only the standard library.

```bash
python3 scripts/verify_package.py
```

**3. Run the included tests.**

```bash
python3 -m unittest discover -s tests -v
```

The verifier checks 12 frozen file hashes, selected counts and proportions, and temporal reporting boundaries. The [CI workflow](.github/workflows/verify.yml) runs the same checks and separately validates a compatible analysis environment. For source analysis requirements and precise limits, see [Reproduction and Verification](reproduce.md).

## Repository Structure

```text
genai-trust-reddit-analysis/
├── .github/workflows/
│   ├── verify.yml
│   └── render-figure.yml
├── scripts/
│   ├── run_day15_rq1_counts.py
│   ├── run_day18_rq2_community.py
│   └── verify_package.py
├── results/
├── figures/
│   ├── rq1_figure.pdf
│   ├── rq1_figure.png
│   └── rq1_figure.webp
├── provenance/
├── tests/
├── data/
│   └── README.md
├── environment.yml
├── reproduce.md
├── CITATION.cff
├── LICENSE
└── README.md
```

The preserved scripts perform actual analysis of verified frozen inputs. The results and figures are frozen research outputs, not newly generated results from this repository's smoke test. Provenance records document methodological decisions, denominator rules, outputs, and checksums. The raster previews of Figure 1 were rendered from the checksum verified frozen PDF without changing its plotted content.

## Data

This study reuses research data released by Pessianzadeh and colleagues. It examines five technical Reddit communities: `ChatGPTCoding`, `webdev`, `programming`, `GitHub`, and `compsci`.

| Archive | Source records | Records with valid analyzed measures |
| --- | ---: | ---: |
| Trust and distrust classification | 8,520 | 8,519 |
| Trust and distrust dimensions | 4,964 | 4,964 |

The classification archive retains one record without a valid classification label. The dimensions archive contains 13 indicators that can cooccur within a record. The primary temporal window spans 2023 H1 through 2025 H1, with December 2022 retained as partial coverage context only.

The original source dataset is available at [Zenodo record 20331918](https://doi.org/10.5281/zenodo.20331918). This is the **source dataset**, not a preprint of the present study. No public SSRN preprint has been verified yet.

All three direct Day 14 inputs and both frozen analytic files were recovered in the preserved local research project, and their recorded SHA256 digests matched. Record level inputs, Reddit post text, user information, and private correspondence are not redistributed here. See [Data Availability](data/README.md).

## Method

The study uses descriptive reporting of released computational classification labels and dimensions. It does not train a new classifier or perform causal analysis or hypothesis testing.

**Classification.** The released categories `Trust`, `Distrust`, `Both`, and `Neither` are summarized within the classification archive. Reported category shares use the 8,519 available valid labels, while the full 8,520 source records remain accounted for.

**Community and temporal descriptions.** Results are presented across the five communities and UTC half year periods, with sparse or unavailable cells identified according to the frozen protocol.

**Measurement and provenance.** The classification and dimensions archives have independent inclusion flows and denominators. The public source release did not establish the source study's full dimension specific field map. Rather than assert a reconstruction, this study adopted the documented replacement estimand `Output_gpt-4.1-2025-04-14_few`, with a locked 13 indicator vocabulary, parsing and exception rules. This replacement does not externally validate the original mixed field procedure. See [D013 decision record](provenance/d013_activation_record.md).

## Reproduction Evidence

### Reported results and verified frozen outputs

| Measure | Submitted manuscript | Independently checked frozen results |
| --- | ---: | ---: |
| Valid classification labels | 8,519 | 8,519 |
| Pooled Neither | 41.7% | 41.7% |
| Pooled Trust | 40.0% | 40.0% |
| ChatGPTCoding Trust | 43.1% | 43.1% |
| programming Trust | 46.2% | 46.2% |
| Dimension records | 4,964 | 4,964 |
| Competence indicator | 70.6% | 70.6% |

### Local reproduction audit, October 25, 2026

| Stage | Verified outcome |
| --- | --- |
| Day 14 | Required direct and analytic frozen inputs recovered; SHA256 checksums matched |
| Day 15 | Descriptive results reproduced byte for byte |
| Day 16 | Tables and raster figures matched; PDF and SVG were visually equivalent |
| Day 17 | Sensitivity outputs reproduced; the original QC gate remains `BLOCKED` |
| Day 18 | Analytical outputs reproduced exactly; only a run specific provenance ID differed |
| Day 20 | Not independently rerun |

Day 16 vector differences were limited to export timestamps and generated internal IDs. The frozen and rerun PDFs rendered identically at the tested resolution; text and collision audits passed. No scientific difference was identified.

**A complete raw-data-to-paper rerun was not established.** Although the verified Day 14 frozen inputs were available and major analysis steps were rerun locally, those inputs are not distributed here and not all downstream paper generating steps are independently executable from this package.

The precise commands, inputs, and outstanding issues are explained in [Reproduction and Verification](reproduce.md). GitHub Actions passing means the **package tests and compatible runtime verification** succeeded; it does not imply an end to end manuscript reproduction.

## Limitations

**Interpretation.** The released labels characterize sampled online discourse records, not verified individual psychological states, user behavior, developer occupations, or population prevalence.

**Measurement.** The dimensions analysis uses a transparent replacement estimand rather than a reconstructed or externally validated source study measurement.

**Temporal coverage.** Some strata contain sparse or unavailable records. The descriptive comparisons do not establish a time trend or a causal mechanism.

**Reproducibility.** The included code and frozen aggregate materials support verification of specific analysis stages, not a complete independent raw data to final manuscript rerun.

**Submission provenance.** The exact journal uploaded PDF has not yet been independently identified from the local candidate build and submission hash records.

**Reuse permissions.** Source data and derived materials have distinct rights and access considerations. The current repository grants no general reuse license pending review of the applicable conditions.

## Citation & Contact

**Submitted manuscript**

Zhan, H. (2026). *Beyond the Aggregate: Trust and Distrust in Generative AI Across Technical Reddit Communities and Time*. Manuscript submitted for peer review.

**Source study and dataset**

Pessianzadeh et al. (2026). *In Generative AI We (Dis)Trust? Computational Analysis of Trust and Distrust in Reddit Discussions*. *Transactions of the Association for Computational Linguistics*.

[Source publication](https://doi.org/10.1162/TACL.a.744) · [Source dataset](https://doi.org/10.5281/zenodo.20331918)

Software citation metadata are in [CITATION.cff](CITATION.cff). An SSRN preprint link will be added only after an actual public preprint is verified.

**Hong Zhan**

[Academic website](https://ivyhongzhan.github.io/Ivyhongzhan/) · [GitHub profile](https://github.com/ivyhongzhan) · [ORCID](https://orcid.org/0009-0002-1862-0913)

Email: [hz2030@alumni.york.ac.uk](mailto:hz2030@alumni.york.ac.uk)
