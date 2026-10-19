# 06 Analytics

One dataset per business or analytical question, ready for the dashboard.

Empty until milestone 04 (Serve). The job holds disabled placeholders for
`01_answer_ap1` to `04_answer_ap4` (#144 to #147), each starting from the fact
gates it reads. The priority table (#178) applies the D-057 rule after the AP2 and AP3
gates (D-051); peer groups were parked, and Similar LGUs (#96) is context only. Dataset names stay deferred until the
analytical questions and output grains are approved.

Built: `ap4_enrollment_trend` (`04_answer_ap4.sql`, gate `90_validate_ap4.sql`, #147,
D-058), one row per city or municipality member and school year: enrollment and
its trend, with the school-age gap as context on the census school years. Its tasks stay
disabled until `fact_school_enrollment` (#196) is published. The build writes a
candidate; the gate publishes it only after every check passes. Files follow
`NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see [File
naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).
