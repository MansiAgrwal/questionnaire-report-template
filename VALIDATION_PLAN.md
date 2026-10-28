# Validation plan

## Defensible scope

A reusable workflow for configurable scoring and participant feedback from fixed-form quantitative questionnaires. The included prototype supports four aggregation methods and researcher-defined text and conditional rules. A claim of compatibility with “mostly any questionnaire”, clinical validity, novelty of generalised feedback, or superiority to other tools is not supported.

## What is completed

- Configuration-driven implementation, named-column CSV input and HTML/Word/JSON output.
- Four invented instrument configurations and exhaustive formula-based scoring checks.
- Boundary, missingness, invalid-code, conditional-text and output-release checks.
- Two illustrative Word reports and reproducible structured outputs.
- Version 0.1.1: two defects found in review fixed (truncated CSV rows; displayed precision), each with a test.


## What would strengthen a publishable evaluation

1. Select three or more actual, permitted instrument configurations with substantively different scoring requirements. Verify every rule and interpretation against the applicable manual, language, population and version. Use public-domain or otherwise permitted material for redistribution.
2. Have independent reviewers prepare expected scores and approved messages for frozen reference cases. Include threshold boundaries, permitted and prohibited missingness, contradictory inputs and interactions between narrative sections. Keep disagreements and adjudication records.
3. Measure numerical agreement, interpretation-band agreement, missingness decisions, omitted or inappropriate statements, report-completion failures and trace completeness. The present synthetic tests cannot supply those human-review outcomes.
4. Compare common tasks with a clearly specified manual/template workflow and at least one suitable existing tool. Measure setup time, correction effort, scoring/report discrepancies and maintainability under changes in item order or instrument version. There is no basis yet for a superiority claim.
5. If claiming usability, run a prospective evaluation with researchers who were not the tool's developers. Report experience, task completion, errors and assistance required. Whether institutional review applies must be determined from the actual evaluation design; no participant recruitment has been undertaken here.
6. Inspect every real-instrument report template before participant release. Retain authorship, study permissions and instrument permissions appropriate to the actual work. The prototype includes only invented wording and thresholds.
