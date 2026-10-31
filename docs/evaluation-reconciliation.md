# Evaluation evidence reconciliation — 2026-10-31

The first overview indexed only selected recent assistant messages and six original
source reports. Missing sources were too easily interpreted as untested methods.
The revised audit reads all eight supplied conversations back to their first
visible message (57,990 initial visible messages plus 158 incremental messages (58,148 total) at the read boundary, excluding platform
and system messages). Audit ranges and counts are in data.json/evaluation_audit.
Only assistant text was retained privately; no raw conversation or credentials
are published. Running agents may have new messages after this boundary.

Added ten completed experiment cells from original files:

- V13 TTC 30k strict held-out threshold study: threshold .975 H4=19/100,
  H8=16/100; threshold .8 H4=5/100, H8=12/100 (one unknown).
- V13 task-event SR follow-up: Mem-0 H4=44/100 (15 unknown), H8=39/100
  (21 unknown); TTC H4=24/100 (3 unknown), H8=16/100 (9 unknown).
- V13 Mem-0 multi-environment camera candidate: H4=18/100 (1 unknown),
  H8=14/100 (11 unknown).

The original V13 pi0.5 single-environment 30k evaluations remain H4=0/100 and
H8=0/100 (one unknown in H8). They are completed results, not untested entries.
A new single-vs-concurrent campaign is still incomplete; source counts are shown
only as success/audited/target, never as final success/100.

SR removes multiple extra safety/hold/clearance requirements. It is a distinct
metric, not improved model performance on the original strict test. The overview
labels SR and strict results explicitly; all prior batches remain in details.
No threshold-study or camera-candidate rates are pooled with other campaigns.

Five-task TTC has no verified dataset/weight delivery or evaluation report in this
inventory. Its evaluation status is unconfirmed; it is not counted as evaluated.
A concrete trained checkpoint is needed before adding it to the deployment queue.
This evidence gap is distinct from the confirmed three-task TTC and pi0.5 tests.

Reproduce original report ingestion with scripts/reconcile_eval_evidence.py on
the workstation that holds the source paths. This never starts/stops other jobs
or changes another agent's files.

The coverage panel records per-conversation lower/upper IDs, message counts,
backward/forward page boundary checks, caught-up flags and timestamps. This is
manual evidence reconciliation with an explicit cutoff, not unattended memory
polling. Tool summaries are not full tool-output audits. The newest seven-task
2/12-vs-2/12 diagnostic and three-task partial paired counts remain separate from
completed formal100 success rates.

## Classification consistency repair

Reproduction at the previous release showed two failures: a task classification
had no complete task-level evaluation list, and Sync only fetched GitHub Issues,
leaving the loaded data.json unchanged. Diagnostics noted in agent summaries were
also absent from the category records.

The shared evaluation index now contains every original campaign, latest shared
score and separately tagged diagnostic. Task classifications list all versions by
default, with dataset/method/type filters and original evidence links. Details use
the same index. Explicit Sync and periodic Sync refresh both the baseline and
shared Issues; a shared-feed failure does not hide a successful baseline refresh.
Versioned script URLs prevent a newly loaded page from mixing stale application
code with the updated baseline.

`node tests/classification-consistency.mjs` was RED for both original symptoms,
then GREEN for the original two checks plus cross-view score/status checks and
five-/seven-task diagnostic visibility. The test changes a fetched score only in
the browser fixture and verifies category, overview and detail agreement; it
never modifies production results or creates a shared issue.
