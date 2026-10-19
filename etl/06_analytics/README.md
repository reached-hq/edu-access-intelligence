# 06 Analytics

One dataset per business or analytical question, ready for the dashboard.

Empty until milestone 04 (Serve). The job holds disabled placeholders for
`01_answer_ap1` to `04_answer_ap4` (#144 to #147), each starting from the fact
gates it reads. The priority table (#178) applies the D-057 rule after the AP2 and AP3
gates (D-051); peer groups were parked, and Similar LGUs (#96) is context only. Dataset names stay deferred until the
analytical questions and output grains are approved. Files follow
`NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see [File
naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).

## AP2 · Classroom pressure (`ap2_classroom_pressure`)

`02_answer_ap2.sql` builds `ap2_classroom_pressure_candidate`, one row per regular city or municipality
for SY 2023-24, from `fact_school_enrollment`, `fact_school_classroom_capacity` and
`dim_city_municipality`. Enrollment is summed to one row per school before the room join.
`learners_per_nsbi_instructional_room` is the sum of complete all-level learners over the sum of
`instructional_classrooms_total` for the same active public schools with rooms above 0. The row also carries
school and learner coverage with their numerators and denominators, missing, zero and absent room counts,
incomplete-enrollment and annex counts, and a NULL reason. `90_validate_ap2.sql` reconciles these
with the facts and publishes `ap2_classroom_pressure` only when no check fails. It reports unresolved
geography and the D-057 outlier fence nationally, as WARN counts in `data_quality_results`. The output is
**provisional**: annexes have no mother-school link (D-044), and the upper tail is still under review.
Its benchmark status is "not applicable" (D-045).
