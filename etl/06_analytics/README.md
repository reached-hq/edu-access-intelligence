# 06 Analytics

One dataset per business or analytical question, ready for the dashboard.

`ap1_school_provision` is implemented by `01_answer_ap1.sql` and published only
after `90_validate_ap1.sql` passes. Its grain is regular city or municipality,
enrollment school year, and reporting level (`ALL`, `ES`, `JHS`, `SHS`). It
keeps LGUs with no school, applies D-050's active and complete-enrollment rules,
uses the fixed 2024 population reference, and carries the barangay screen and
upper-bound label without ranking barangays.

The job retains disabled placeholders for `02_answer_ap2` to `04_answer_ap4`
(#145 to #147), each starting from the fact gates it reads. The priority table
(#178) applies the D-057 rule after the AP2 and AP3
gates (D-051); peer groups were parked, and Similar LGUs (#96) is context only. Dataset names stay deferred until the
remaining analytical questions and output grains are approved. Files follow
`NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see [File
naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).
