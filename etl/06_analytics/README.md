# 06 Analytics

One dataset per business or analytical question, ready for the dashboard.

Empty until milestone 04 (Serve). The job holds disabled placeholders for
`05_assign_peer_group` (#148), `01_answer_ap1` to `04_answer_ap4` (#144 to
#147), and `06_compare_peer_groups`. Each AP starts from the fact gates it reads;
the peer comparison for AP2 and AP3 waits for their gates and the peer-group
gate, so the core ratios do not wait for #142 (D-051). Dataset names stay deferred until the
analytical questions and output grains are approved. Files follow
`NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see [File
naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).
