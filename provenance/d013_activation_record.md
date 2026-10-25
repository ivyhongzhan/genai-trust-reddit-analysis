# D-013 contingency activation record

**Date:** 2026-09-25  
**Decision outcome:** PASS — the previously approved no-response contingency is activated.  
**Authorization:** Researcher instruction on 2026-09-25 to execute D-013 after the 2026-09-23 23:59 UTC deadline, with no missing Mixtral file received.

## Trigger evidence

- The revised author/source-response deadline in D-013 was 2026-09-23 23:59 UTC; it had passed when this record was created.
- The researcher reported that no missing Mixtral file had been received.
- The local released dimensions file contains 135,061 rows and seven released `Output_` fields, but no `final_mixtral_output` field.
- The local dimensions input SHA-256 is `e921bb5a9de38fd5e8ee6e49e9c78208307b720b03c70515d5296a9fe8d85456`.

## Activated dimension estimand

- **Primary field:** `Output_gpt-4.1-2025-04-14_few`.
- **Sensitivity fields:** `Output_gpt-4.1-2025-04-14`, `Output_gpt-4.1-nano-2025-04-14`, `Output_gpt-4.1-nano-2025-04-14_few`, `Output_gpt-4o-2024-11-20`, `Output_gpt-5-mini-2025-08-07`, and `Output_gpt-5-mini-2025-08-07_few`.
- Each sensitivity field remains a separate pipeline with its own eligible denominator and exceptions. No cross-field complete-case sample is authorized.

## Activated parser, vocabulary, and exception policy

- Preserve every raw output string unchanged. For a present, nonblank value, split on literal commas and trim leading/trailing whitespace from every token.
- Exact allowed vocabulary: `Competence`, `Reliability`, `Familiarity`, `Integrity`, `Transparency`, `Benevolence`, `Incompetence`, `Unreliability`, `Unfamiliarity`, `Dishonesty`, `Deception`, `Opaqueness`, and `Malevolence`.
- Null, missing, or all-whitespace output is retained as a missing-output exception and excluded only from that field's eligible denominator. It is never encoded as dimension absence.
- Empty, duplicate, or unexpected tokens are retained as exceptions and are never corrected, coerced, or silently dropped.
- The five-community dimensions archive remains archive-specific (`N = 4,964` source records). The exact eligible denominator is field-specific after applying the activated exception policy.

## Required manuscript limitation

The uniform-field estimand is a transparent replacement protocol selected for completeness and parseability after the source study's mixed, dimension-specific output map could not be reproduced from the public release. It does not reproduce or validate the original mixed-field estimand. The six alternative released fields are measurement-sensitivity pipelines, not external validation.

## Independent gates unaffected

This activation does not approve the classification reporting convention, archive joining, temporal/sparsity rule, uncertainty/display method, model, results, figures, or interpretations.
