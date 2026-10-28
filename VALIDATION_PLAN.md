# Validation plan

## Defensible scope

A reusable workflow for configurable scoring and participant feedback from fixed-form quantitative questionnaires. The prototype supports sums, means, weighted aggregates and count rules; linear conversions and lookup tables chosen by group; computed items from clock times and numeric variables; and researcher-defined conditional and filled report text. A claim of compatibility with “mostly any questionnaire”, clinical validity, novelty of generalised feedback, or superiority to other tools is not supported.

## What is completed

- Configuration-driven implementation, named-column CSV input and HTML/Word/JSON output.
- Eight invented instrument configurations and formula-based scoring checks (exhaustive where the response space allows, seeded random otherwise).
- Boundary, missingness, invalid-code, conditional-text and output-release checks.
- Four illustrative Word reports (from three examples) and reproducible structured outputs.
- Version 0.1.1: two defects found in review fixed (truncated CSV rows; displayed precision), each with a test.
- Version 0.2.0: variables, computed items, count rules, lookup tables and filled report text, each compared with separately written calculations; deliberate-error checks on the new tests.

## Coverage: how much of real questionnaire practice can it express?

The design goal is an engine that researchers can configure for the questionnaires they use. That claim needs measuring, not asserting.

1. **Define the target class** before testing, for example fixed-form self-report instruments scored from item responses, with optional norm tables and cut-offs.
2. **Fix a sampling frame in advance**, so that instruments cannot be chosen because they work. For example, the most frequently used freely available instruments in a named field, or a random sample from a measurement database. Record the frame, the date and the inclusion rules.
3. **Configure each instrument from its manual.** Code each one as fully expressible, expressible with a workaround, or not expressible, with the reason (for example skip logic, IRT scoring, calendar dates, multi-informant input). Keep the configurations.
4. **Check scoring accuracy** for expressible instruments that permit it. Compare outputs with the manual's worked examples, or with independent hand-scoring of frozen cases that include boundaries and missing-data patterns.
5. **Repeat the coverage coding** for one or more existing tools on the same sample.
6. **Report** the proportion fully expressible with a confidence interval, the reasons for failure, and scoring agreement. A second person should code a subset independently, and their agreement should be reported.

## What would strengthen a publishable evaluation

1. Select three or more actual, permitted instrument configurations with substantively different scoring requirements. Verify every rule and interpretation against the applicable manual, language, population and version. Use public-domain or otherwise permitted material for redistribution.
2. Have independent reviewers prepare expected scores and approved messages for frozen reference cases. Include threshold boundaries, permitted and prohibited missingness, contradictory inputs and interactions between narrative sections. Keep disagreements and adjudication records.
3. Measure numerical agreement, interpretation-band agreement, missingness decisions, omitted or inappropriate statements, report-completion failures and trace completeness. The present synthetic tests cannot supply those human-review outcomes.
4. Compare common tasks with a clearly specified manual/template workflow and at least one suitable existing tool. Measure setup time, correction effort, scoring/report discrepancies and maintainability under changes in item order or instrument version. There is no basis yet for a superiority claim.
5. If claiming usability, run a prospective evaluation with researchers who were not the tool's developers. Report experience, task completion, errors and assistance required. Whether institutional review applies must be determined from the actual evaluation design; no participant recruitment has been undertaken here.
6. Inspect every real-instrument report template before participant release. Retain authorship, study permissions and instrument permissions appropriate to the actual work. The prototype includes only invented wording and thresholds.
