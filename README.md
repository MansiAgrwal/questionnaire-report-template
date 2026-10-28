# Configurable questionnaire report template

Scoring rules and participant reports for fixed-form questionnaires, defined in a JSON configuration instead of code. A researcher declares items, response codes, scales, scoring rules, conversions, cut-offs and report wording. The same engine then scores a CSV export and writes HTML, editable Word and JSON audit records. The engine does not invent item meanings, cut-offs, norms or advice.

The aim is a single engine that can be configured for many questionnaires a researcher may want to report on. Whether it achieves that is an empirical question, and it has not been tested yet: `VALIDATION_PLAN.md` describes how to measure the share of real instruments it can express. All included instruments, thresholds, norm tables and wording are invented demonstrations. This is a research prototype, not a clinically validated product.

## Quick start

Python 3.10 or later:

```bash
python -m pip install -r requirements.txt
python test_qreport.py
python qreport.py --config examples/dynamic_text.json --data examples/dynamic_text.csv --out my_reports --docx
```

Choose an empty output directory for each run. Omit `--docx` if you need only HTML and the JSON audit records. Scoring, HTML and JSON use the Python standard library; Word output uses python-docx. The program makes no network calls and sends no reports or messages.

## What a configuration can express

**Responses.** One row per participant, with named column mappings and unique participant identifiers. Responses can be integer or continuous with declared bounds, or labelled codes mapped explicitly to scores. Items can be reverse-scored. Declared missing codes are kept distinct from invalid codes.

**Other variables** (schema 1.1). Columns that are not items: numeric (for example age), categorical (for example sex) or 24-hour clock times. They can select norm tables, enter conditions and feed computed items.

**Computed items** (schema 1.1). An item can be calculated from other items and variables with addition, subtraction, multiplication, division, minimum, maximum, absolute value and minutes between two clock times (wrapping past midnight). The result can be mapped to a score through ordered intervals, with any boundary assigned to either side. This covers rules such as "sleep efficiency = hours asleep / time in bed; below 65% scores 3". A missing input leaves the computed item missing. An impossible calculation, such as division by zero, blocks the report.

**Scale scores.**
- Sums, means, weighted sums and weighted means, with overlapping subscales allowed.
- Count rules (schema 1.1): the number of items meeting a threshold, with optional per-item thresholds. Combined with conditions, this expresses rules such as "at least four items at 2 or above, including item 1 or item 2".
- Positive linear conversions, such as multiplying by a fixed factor.
- Lookup tables (schema 1.1): an exact table for every whole raw score, or an interval table. Separate tables can be chosen by group conditions on variables, for example age band and sex for norm-referenced T-scores. The raw score can be rounded half up or up before lookup. A table is chosen only when its group can be determined; otherwise the scale is left unscored with the reason recorded.

**Missing responses.** By default every item must be answered. Proration is allowed only with a minimum answered count and a written justification, and requires identical item bounds. Count scales always require every item.

**Interpretation.** Contiguous, non-overlapping bands on the final score. A band can hold a report for human review. Eligibility requirements, such as a completion flag, block release when unmet.

**Report text.** Each band has its own text. Conditional sections are combined with `all`, `any` and `not` over items, scales and variables, using three-valued logic: an unknown input never triggers a paragraph. Section text can include values filled from the record (schema 1.1):
- the wording for the participant's response option;
- the highest-rated item in a scale, with ties named together, resolved by configuration order, or withheld;
- a scale's displayed score or band.

If a value cannot be determined, the section is withheld and the reason recorded.

**Outputs.** HTML, editable Word and JSON reports. The JSON records item-level transformations, computed values, variables, scoring decisions, the table used, section decisions, and input and configuration hashes.

## What it cannot express yet

- IRT or Rasch scoring and adaptive tests.
- Skip logic, where later items depend on earlier answers.
- Multi-informant reconciliation, and more than one row per participant.
- Longitudinal reliable-change indices.
- Calendar dates (clock times only), free-text responses and Excel or SPSS imports.
- Imported Word templates; the engine supplies one editable layout.
- Proration across items with different bounds.

Each would need its own implementation and tests. The tool does not estimate reliability, establish validity, choose cut-offs, license items, infer diagnoses or decide whether feedback is appropriate.

## Examples

| Configuration | Demonstrates | Synthetic values |
| --- | --- | --- |
| `examples/likert.json` | Reverse-scored sum and mean, conditional narrative | Four items, 0–4 |
| `examples/weighted_mean.json` | Categorical recoding and unequal weights | Four items, four labelled choices |
| `examples/knowledge.json` | Keyed binary responses and percentage conversion | Five A/B-coded items |
| `examples/prorated.json` | Weighted sum with an explicit missing-response rule | Four items, 1–5; at least three answered |
| `examples/count_rule.json` | Count of items at threshold, per-item threshold, combined rule | Six items, 0–3 |
| `examples/norm_table.json` | Prorated raw sum rounded up and converted by age- and sex-specific tables | Four items, 1–5; age, sex |
| `examples/sleep_diary.json` | Clock times and durations computed into component scores, then summed | Bedtime, wake time, latency, hours, two items |
| `examples/dynamic_text.json` | Response wording, the highest-rated item with tie rules, scores in sentences | One duration item, six rated reasons |

Each configuration has a CSV example. `sample_outputs/` contains the resulting JSON audit files, 12 HTML reports and four Word reports (from the likert, prorated and dynamic_text examples). No real participant information is included.

## Read the output status

`ready` means every configured scale could be scored under the supplied rules. `partial` means at least one scale was scored and another had insufficient answers. `unscored` means no scale could be scored. `blocked` means an invalid response, an invalid variable, an impossible computation or a failed eligibility requirement prevents report release. `held_for_review` means a configured band requests human review. Only ready and partial records receive an HTML/Word report; other records receive an audit JSON record. Partial reports identify unscored scales instead of assigning a score of zero.

Prorated scores are labelled in the report. The software follows the configured rule; it cannot establish that proration is justified, and the missing-data literature generally prefers other methods. Band assignment and conditions use unrounded scores, which the JSON record preserves. Reports show scores rounded half up to the scale's `display_decimals` (default 2, trailing zeros removed). A score just below a band boundary can therefore display as the boundary value while sitting in the lower band, for example 7.999 shown as 8.

## Verification completed

`test_qreport.py` runs 39 tests; all pass (`validation_results.json`). Each scoring feature is compared with a calculation written separately in the test file:
- **Original four configurations:** 2,209 enumerated response profiles; 2,663 scored scales checked and 171 profiles that must stay unscored.
- **Count rule:** all 4,096 response profiles, including the combined rule.
- **Lookup tables:**
  - all 1,296 response-and-missingness patterns under each of nine age and sex combinations, including missing age or sex;
  - every raw score through an interval table;
  - half-up rounding before an exact table.
- **Computed items:** 3,000 seeded random sleep-diary records, including missing values and zero time in bed, with interval boundaries and clock arithmetic across midnight checked separately.
- **Dynamic text:** 250 records covering every rating pattern in each area and each tie rule.
- **Other tests:** invalid inputs, configuration errors, truncated CSV rows, HTML escaping, provenance and release holds.

To check that the tests can fail, six deliberate errors were introduced into the engine one at a time. Five were caught. The sixth did not change behaviour: bins are searched in order, so a shared boundary always falls to the earlier bin. The tests execute 87% of the engine's statements and branches; most of the rest are configuration error messages.

These checks were written alongside the implementation. They show that the code follows its specification; they cannot show that a configured rule matches a real instrument's manual. No real instrument, external user, reviewer agreement or clinical outcome has been evaluated.

## Changes

**0.2.0.** Schema 1.1 adds variables, computed items, count rules, lookup tables and filled section text. Schema 1.0 configurations are still accepted and give identical scores, bands and configuration hashes. The JSON records now also include the canonical response code and a variable trace.

**0.1.1.** Two defects in 0.1.0 were found in review, and each now has a test that fails on 0.1.0:
- **Truncated CSV rows.** A row with fewer fields than the header had its absent fields read as missing answers, so under a proration rule it was prorated and released as `ready`. The batch now stops and writes nothing.
- **Unrounded scores.** Reports printed exact decimal scores, such as 1.666666666666666666666666667. They now round for display.

Tests were also added for paths 0.1.0 never exercised: the `any` operator, the `eq`, `ne` and `lt` comparisons, the three-valued truth tables and proration of a mean.

## Adapting a configuration

Start from the example closest to your instrument and see `CONFIGURATION_GUIDE.md`. Declare scoring, conversion tables and interpretation from the instrument's manual, then add frozen reference cases. Check boundaries, each missing-response pattern, invalid codes, norm-group edges and conditional-message interactions before applying it to research data.

Band text permits only `{{score}}`, `{{band}}`, `{{answered}}` and `{{items}}`. Section text permits only tokens declared in its `fill`. No Python expressions are evaluated. Unexpected configuration fields and duplicate JSON keys are rejected.

Report filenames use a hash of the participant ID. The participant ID remains in the report and audit record, so outputs must be handled as participant data if you use real identifiers.

## Related work

General questionnaire scoring and automated feedback already exist, for example:
- [formr](https://doi.org/10.3758/s13428-019-01236-y) (automated feedback within a study framework);
- [Scorify](https://github.com/uwmadison-chm/scorify) (configurable scoring of self-report questionnaires);
- [ScoreMe's questionnaire schema](https://github.com/circadia-bio/ScoreMe/blob/main/docs/questionnaire-schema.md);
- [PROscorer](https://cloud.r-project.org/web/packages/PROscorer/index.html) (scoring functions for specific patient-reported outcome measures).

No first-in-field or superiority claim is made. `VALIDATION_PLAN.md` describes the evidence a comparison would need.

## Attribution

The original study-specific workflow is Mansi Agarwal's [personalized-feedback-reports](https://github.com/MansiAgrwal/personalized-feedback-reports). Version 0.1.0 of this prototype, its tests and documentation were prepared with OpenAI Codex assistance at the researcher's request. Claude (Anthropic) reviewed 0.1.0, fixed the defects listed under 0.1.1, and implemented and tested the schema 1.1 extensions in 0.2.0 at the researcher's request. Independent instrument-based validation remains necessary before participant use. No study-owned questionnaire items or report templates are reproduced here.

## License

Prototype source code and invented examples: MIT, as stated in `LICENSE`. Instrument wording, manuals and normative data added later retain their own permissions and conditions.
