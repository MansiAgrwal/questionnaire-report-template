# Configuration guide

Use the supplied JSON files as executable examples. Schema versions `1.0` and `1.1` are supported. Version 1.1 adds the fields marked (1.1) below; a 1.0 configuration may not use them, and 1.0 configurations score exactly as before. Unknown fields and duplicate JSON keys are errors.

## Top-level fields

Required: `schema_version`, `questionnaire_id`, `title`, `instrument_version`, `scoring_reference`, `id_column`, `items`, `scales`.

Optional: `introduction` (literal text), `missing_codes` (default empty, null and `NA`), `eligibility`, `sections`, `variables` (1.1), `derived_items` (1.1).

Use stable identifiers beginning with a letter and containing only letters, digits and underscores for questionnaire, item, scale, band and section IDs. CSV column names are mapped explicitly and do not have to match those IDs. Participant IDs must be nonempty and unique in a batch.

## Items

An item needs `id`, `column`, `min`, `max`. Bounds describe scores after any raw-code recoding and before reversal. Optional `reverse: true` applies `min + max - recoded_score`. Optional `allow_decimal: true` permits fractional scored responses. Optional `recode` maps raw codes to numeric scores; unspecified codes are invalid, rather than silently becoming missing.

Optional (1.1): `label`, a short description used when a report names the item, and `response_labels`, a map from every valid response code to the wording a report should use for it. Every valid code must be labelled exactly once.

For ordinary numeric items, integer values within the bounds are accepted unless decimal responses are enabled. Numeric strings such as `1` and `1.0` are canonicalised to the same code. Missing codes cannot overlap otherwise valid responses. For instance, zero cannot simultaneously mean both a valid response and missing data.

## Variables (1.1)

Variables are input columns that are not questionnaire items. Each has `id`, `column` and `type`:

- `numeric`: requires `min` and `max`; optional `allow_decimal`. Values outside the bounds block the report.
- `categorical`: requires `codes`, a list of permitted values. Other values block the report.
- `time`: a 24-hour clock time written `H:MM` or `HH:MM`, stored as minutes after midnight.

Missing codes apply to variables as to items, and cannot overlap valid values. Variables can appear in conditions, choose lookup tables, and feed computed items (numeric and time types only).

## Computed items (1.1)

`derived_items` are calculated after the ordinary items and variables, in list order. Each needs `id`, `min`, `max` and `compute`; `label`, `bins` and `allow_decimal` are optional. Once computed, a derived item can be used in scales and conditions like any other item.

`compute` is an expression tree. A node is `{"const": n}`, `{"item": id}` (the scored value of an ordinary item or an earlier derived item), `{"variable": id}`, or `{"op": name, "args": [...]}`. The operations are `add`, `sub`, `mul`, `div`, `min`, `max`, `abs` and `minutes_between` (end minus start, wrapping past midnight, from 0 to 1439). Expressions may nest up to 32 levels. If any input is missing, the derived item is missing. Division by zero, a value outside the configured bins, or a value outside `min`/`max` blocks the report.

`bins` map the computed value to a score through ordered intervals with `lower`, `upper` and `value`. The first `lower` and the last `upper` may be `null` for an open end. Lower bounds are inclusive. Any bin may set `upper_inclusive: true`; the shared boundary then belongs to that bin rather than the next. Bins must be contiguous, and each `value` must lie within the item's bounds.

## Scales

Required: `id`, `label`, `items` (unique item IDs), `method` (`sum`, `mean`, `weighted_sum`, `weighted_mean`, or `count` in 1.1).

**Count scales (1.1).** `method: "count"` counts the items whose scored value meets `criterion`, written `{"op": "ge", "value": 2}`. `item_criteria` can give individual items their own criterion. Count scales require every item to be answered, and do not take weights or proration. Their range is 0 to the number of items.

Optional: `weights` mapping item IDs to positive weights. Unspecified weights are one. Supply weights only for weighted methods. `multiplier` must be positive and defaults to one; `offset` defaults to zero. These apply after aggregation and any proration. No normative conversion is inferred. `display_decimals` (an integer from 0 to 6, default 2) sets how the score is shown in reports: rounded half up, with trailing zeros removed. It does not affect bands, conditions or the exact score in the JSON record.

`missing_policy` defaults to `{"method":"complete"}`. A proration policy must name `method: "prorate"`, `minimum_answered` and a nonempty `justification`. For sums, the observed weighted sum is multiplied by total configured weight divided by answered-item weight. Means use the answered-item weighted mean. Proration requires the same lower and upper scored bounds for every item in that scale. These are software rules, not an endorsement of proration for a real instrument.

**Lookup tables (1.1).** `lookup` replaces `multiplier`/`offset` and converts the raw score through a table. It needs `reference` and `tables`, and accepts `round_raw` (`none`, `half_up` or `up`), applied to the raw score before lookup. Each table has an `id`, a `type` and `rows`, plus an optional `group` condition on variables. Tables are tried in order:
- the first whose group is true is used;
- a table without `group` always applies;
- if a group condition is unknown because a variable is missing, the scale is left unscored and the reason recorded;
- if no table applies, the scale is also left unscored.

An `exact` table lists `{"raw": r, "score": s}` for every whole raw score in the scale's range, exactly once. It needs whole-number raw scores: integer items, integer weights and complete scoring, or a `round_raw` setting. An `interval` table lists `{"lower", "upper", "score"}` intervals covering the raw range, like bands. Bands then apply to the converted score; their range runs from the lowest to the highest converted score across all tables.

Interpretation is optional. If `bands` are supplied, `interpretation_reference` is required. Each band has `id`, `label`, `lower`, `upper`, `upper_inclusive` and optional `text`, `hold`. Band order must cover the complete computed score interval without gaps or overlaps. Only the final band sets `upper_inclusive: true`; earlier bands set it false. A band can set `hold: true` to withhold a report for review.

Band text accepts `{{score}}`, `{{band}}`, `{{answered}}` and `{{items}}`; `{{score}}` is the displayed, rounded score. The engine uses unrounded scores for decisions. Text is researcher-authored and not generated by a language model during reporting.

## Conditional sections

Every section needs `id`, `title`, `text` and `source`. Optional `when` specifies its inclusion condition. Without `fill`, section text is literal.

**Filled text (1.1).** `fill` declares tokens that can appear in the section text as `{{token}}`. Every token in the text must be declared, and every declared token must be used. Each token is one of:

- `{"response_label": item}`: the item's `response_labels` wording for the participant's response;
- `{"top_items": scale, "ties": "all"}`: the `label` of the highest-scored item in the scale (after reversal). Every item in the scale needs a `label`. When items tie, `all` names them together ("A and B"), `first` uses configuration order, and `withhold` withholds the section;
- `{"score": scale}` or `{"band": scale}`: the displayed score or band label.

If a value cannot be determined, for example because the item was missing, the scale was not scored or `withhold` applied, the section is withheld and the decision recorded. Filled text is escaped in HTML.

Leaf example:

```json
{"scale":"total", "op":"ge", "value":8}
```

Use `item` instead of `scale` to test the numeric item value after recoding and reversal, or `variable` (1.1) to test a variable. Categorical variables accept only `eq` and `ne` with one of their codes; time variables accept a value in minutes or as `HH:MM`. Operators are `eq`, `ne`, `lt`, `le`, `gt`, `ge`. Combine predicates with `{"all":[...]}`, `{"any":[...]}` or `{"not":{...}}`.

A missing or invalid value makes that predicate unknown. Under three-valued logic, not-unknown stays unknown, false-and-unknown is false, and true-or-unknown is true. A section is included only when its final condition is true. Its inclusion, exclusion or withholding is recorded in `section_trace`.

## Eligibility

Optional eligibility entries have `column`, `equals`, and `reason`. Every input record must contain those columns. If a value does not match the required code, the report is blocked. For example, an explicitly configured completion code can be required before a participant report is released.

## Release and audit

A CSV row with more or fewer fields than the header stops the batch before any report is written. The engine records response transformations, variables, computed values, score status, missing/invalid item IDs, exact scores, the lookup table and raw score used, bands, message decisions, filled values and configuration identity. The batch manifest records the input CSV hash. JSON logs may contain response data and must be handled with the same care as the source data.

Changing a score, label, source or version changes the canonical configuration hash. DOCX archives may have different internal timestamps across runs; the deterministic guarantee concerns scores, decisions and JSON content, not byte-identical Word files.
