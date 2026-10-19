# 06 Analytics

One dataset per business or analytical question, following the approved
[metric specification](../../docs/business/metric-specification.md).

## AP3 teacher pressure

`03_answer_ap3.sql` builds
`edu_access.06-analytics.ap3_teacher_pressure_candidate`.

Grain: one regular city or municipality, enrollment school year, and
education level (`ES`, `JHS`, or `SHS`).

Every regular LGU is retained, including those without an active public
school offering the level.

The output includes:

- learners per teacher;
- school and learner coverage;
- incomplete-enrollment and missing-capacity counts;
- zero-teacher school and annex diagnostics;
- the four locally funded teacher subtotals;
- personnel-source availability and a reason when the ratio is NULL.

Funding subtotals are already included in the teacher count and must not
be added to it again.

A zero-teacher annex contributes its complete enrollment to the ratio
numerator and learner coverage, but not to usable-teacher school coverage.
NULL teacher counts do not receive this exception. A ratio without a
positive teacher denominator stays NULL.

The output is labelled `project-defined` and `provisional`.
Benchmark status is `not applicable` (D-045, D-047).

## Validation and publication

`90_validate_ap3.sql` independently recomputes expected measures from Gold.
It checks the LGU-year-level grid, unique keys, identity, availability,
counts, enrollment, teachers, funding splits, arithmetic, and labels.

The gate publishes `ap3_teacher_pressure` only when every FAIL-level
check passes. A failure keeps the last published output.

Run the local tests with:

```bash
python -m pytest tests/test_analytics_ap3.py -q
```

## Implementation status

Local tests use made-up Gold inputs. The AP3 job tasks remain disabled
until the required Gold inputs are ready.

Real-data reconciliation and Databricks validation are to follow.
The sensitivity teacher-total requirement in #146 remains unresolved,
so this implementation does not complete every acceptance criterion.

Priority tiers and ranking belong to #178 under D-057.

AP1, AP2, and AP4 are separate work under #144, #145, and #147.