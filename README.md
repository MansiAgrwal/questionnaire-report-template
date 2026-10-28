# Configurable questionnaire report template

A standalone prototype for scoring **fixed-form quantitative questionnaires** and producing participant reports from CSV exports. Instruments, scoring, interpretation and conditional text are configured in JSON. The scoring engine does not invent item meanings, cut-offs, norms or advice.

This is a working extension in scope from the study-specific `personalized-feedback-reports` project. It is a separate implementation supplied for review, not a published or clinically validated product. All included instruments and interpretation bands are invented demonstrations.

## Quick start

Python 3.10 or later:

```bash
python -m pip install -r requirements.txt
python test_qreport.py
python qreport.py --config examples/likert.json --data examples/likert.csv --out my_reports --docx
```

Choose an empty output directory for each run. Omit `--docx` if you need only HTML and the JSON audit records. CSV/JSON/HTML scoring uses the Python standard library; Word output uses python-docx. The program makes no network calls and sends no reports or messages.

## What is supported

- One row per participant; named column mappings and unique participant identifiers.
- Numeric integer or continuous responses with declared bounds; explicit raw-code-to-score maps.
- Reverse scoring using the declared scored bounds.
- Sums, means, weighted sums and weighted means; overlapping subscales are allowed.
- Positive affine conversions, such as multiplying a raw score by a fixed factor.
- Complete scoring, or explicitly permitted proration with a minimum answered count and written justification. Proration in this prototype requires identical scored item bounds.
- Contiguous, non-overlapping interpretation bands. All lower bounds are inclusive; upper bounds are exclusive except the last.
- Literal feedback text for each band and conditional sections based on item or scale values. Conditions support `all`, `any`, `not` and six numeric comparison operators. An unknown input stays unknown under `not` and does not trigger a paragraph.
- Eligibility requirements and band-triggered manual-review holds.
- HTML, editable Word and machine-readable JSON outputs; input and configuration hashes and item-level scoring traces.

## What an instrument author must supply

Copy the closest JSON example and provide the item column names, valid response codes, reversal rules, subscale membership, weights, missing-response policy, conversions, interpretation boundaries and approved wording. Include the instrument version and scoring/interpretation references. These definitions must be checked against the actual scoring manual and the intended population and language.

The prototype does not estimate reliability, establish construct validity, select clinical cut-offs, license questionnaire items, infer diagnoses, or decide whether feedback is appropriate. It does not currently implement demographic norm tables, IRT/Rasch scoring, adaptive tests, item-response-dependent branching scores, multi-informant reconciliation, longitudinal reliable-change indices, Excel/SPSS imports, a GUI, or imported Word-template replacement. Those require explicit additional implementations and validation. The included Word renderer supplies one editable report layout.

## The four examples

| Configuration | Purpose | Synthetic values |
| --- | --- | --- |
| `examples/likert.json` | Reverse-scored sum and mean, with conditional narrative | Four items, 0–4 |
| `examples/weighted_mean.json` | Categorical recoding and unequal weights | Four items, four labelled choices |
| `examples/knowledge.json` | Keyed binary responses and percentage conversion | Five A/B-coded items |
| `examples/prorated.json` | Weighted sum with an explicit missing-response rule | Four items, 1–5; at least three answered |

Each configuration has a CSV example. `sample_outputs/` contains the resulting JSON audit files, HTML reports and two illustrative Word reports. These files contain no real participant information.

## Read the output status

`ready` means every configured scale could be scored under the supplied rules. `partial` means at least one scale was scored and another had insufficient answers. `unscored` means no scale could be scored. `blocked` means an invalid response or failed eligibility requirement prevents report release. `held_for_review` means a configured band requests human review. Only ready and partial records receive an HTML/Word report; other records receive an audit JSON record. Partial reports identify unscored scales instead of assigning a score of zero.

Prorated scores are labelled in the report. The software follows the configured rule; it cannot establish that proration is psychometrically justified. Band assignment and conditional text use unrounded decimal scores, which the JSON record preserves. Reports show each score rounded half up to the scale's `display_decimals` (default 2, trailing zeros removed). A score just below a band boundary can therefore display as the boundary value while sitting in the lower band, for example 7.999 shown as 8.

## Verification completed

`test_qreport.py` runs 25 tests. Four enumerate 2,209 synthetic response profiles and compare 2,663 scored scales with closed-form formulas; 171 profiles must remain unscored. The others cover invalid responses, exact band boundaries, column-order invariance, configuration errors, missing input columns, truncated CSV rows, displayed precision, proration of a weighted mean, all six comparison operators, the three-valued truth tables for `all`, `any` and `not`, duplicate participant IDs, release holds, HTML escaping and provenance. Results are in `validation_results.json`.

These tests were created with the implementation, and the reference formulas restate the same rules, so they check consistency, not whether the rules are right. They are not externally reviewed scoring manuals. No external users, clinical outcomes or real-instrument narrative validity have been evaluated. The tests do not establish that the tool works for “mostly any questionnaire”.

## Changes in 0.1.1

Two defects in 0.1.0 were found in review; each now has a test that fails on 0.1.0.

- **Truncated CSV rows.** A row with fewer fields than the header had its absent fields read as missing answers. Under a proration rule the record was prorated and released as `ready`. The batch now stops with an error and writes nothing, as it already did for absent columns.
- **Displayed precision.** Reports printed exact decimal scores, such as 1.666666666666666666666666667 for a weighted mean. They now round for display, as described above. Scores, bands and decisions are unchanged; the configuration hashes of the examples are unchanged.
- **Tests added** for paths 0.1.0 never exercised: the `any` operator, three of the six comparison operators (`eq`, `ne`, `lt`), the full three-valued truth tables, and proration of a mean.

## Adapting a configuration

`examples/likert.json` is the starting template. Change identifiers and source columns; declare scoring and interpretation from the relevant manual; then add frozen reference cases to a separate validation file. Check lower and upper boundaries, each missing-response pattern, invalid codes and any conditional-message interactions before applying it to research data.

Section text is literal. Band text permits only `{{score}}`, `{{band}}`, `{{answered}}` and `{{items}}`. No Python expressions are evaluated. Unexpected configuration fields and duplicate JSON keys are rejected.

Report filenames use a hash of the participant ID. The participant ID remains in the report and audit record, so the outputs must be handled as participant data if you later use real identifiers. Hash-based filenames do not anonymise the report contents.

## Publication status and related work

General questionnaire scoring and automated feedback already exist. Relevant predecessors include [formr](https://doi.org/10.3758/s13428-019-01236-y), [Scorify](https://github.com/uwmadison-chm/scorify), and [ScoreMe's questionnaire schema](https://github.com/circadia-bio/ScoreMe/blob/main/docs/questionnaire-schema.md). No first-in-field or superiority claim is made. `VALIDATION_PLAN.md` describes the evidence needed for a fuller development and validation study.

## Attribution

The original study-specific workflow was described in Mansi Agarwal's [personalized-feedback-reports](https://github.com/MansiAgrwal/personalized-feedback-reports) repository. This new prototype, test suite and documentation were prepared with OpenAI Codex assistance at the researcher's request. Claude (Anthropic) reviewed version 0.1.0 and fixed the two defects listed under Changes in 0.1.1. Independent instrument-based validation remains necessary before participant use. No study-owned questionnaire items or original report templates are reproduced here.

## License

Prototype source code and invented examples: MIT, as stated in `LICENSE`. Instrument wording, manuals and normative data added later retain their own permissions and conditions.
