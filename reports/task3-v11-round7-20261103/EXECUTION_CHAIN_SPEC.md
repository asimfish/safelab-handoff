# T-1035 / interval-end13-linear-fd-v1.1-r7

Status: candidate; expert trajectory parity has NOT passed. Do not substitute this specification for admission evidence.

## Inputs and timing

- Physics step: dt = 1/120 s. Observation/action-label rate: 15 Hz, 8 native ticks per label.
- Joint order: the original ordered arm7 + hand6; absolute targets in radians.
- A label is the last valid native target in its 8-tick interval, with padded entries excluded. Ten original episodes have been checked over all valid labels: maximum target difference is exactly zero.
- Execute only the requested first h4 or h8 action labels of a predicted chunk, then obtain a new observation. Prediction chunk length is independent of execution horizon.

## Commands

Let q_prev be the last **commanded** 13-vector, not the current measured state. For one label q_end and j = 1..8:

    q[j] = q_prev + (j/8) * (q_end - q_prev)
    v[j] = (q_end - q_prev) / (8*dt)

Write both vectors to all 13 controlled joints. The hand follows the same interpolation and finite-difference rule. The new candidate has no arm-only feed-forward ramp or ±0.5 clipping. Original current-state gravity compensation is retained; physics, object initial states, gains, rendering and success thresholds are not changed by this controller patch.

The old evaluated controller `V13_position_linear8_curoboFF_ramp_v1` differs: its arm velocity uses clipped finite differences, then a frame-to-frame ramp; hand feed-forward is zero. Historical results from that controller must not be relabeled as the new chain.

## Acceptance

Replay the loader labels from five left and five right training episodes through this chain; compare with native 120Hz expert recordings. Record per-joint, arm, hand and overall measured-joint RMSE, not only target-command error. Overall 13-joint RMSE must be <=0.005 rad. With placement-v1.1 scoring, endpoint successes must be at least native successes minus one. Record raw 120Hz controls/state and both placement-v1.1 and strict-v1 oracle outputs.

The earlier successful execution index check does not establish trajectory parity. Earlier completed expert replay: native 6/10, old endpoint 4/10 under placement scoring. The first new-chain batch encountered BOS FUSE ENOMEM/EINVAL; its 10 born trials are unknown, its other 10 were not started. A separate RAM-buffered recorder I/O canary is underway. No new-chain admission is claimed.

## Files

- `unified_interval_end13.py` and `test_unified_interval_end13.py`: reference formulas and 8 focused checks.
- `portable_placement.py`: portable scoring entry; `frozen-strict-manifest.json` pins its original strict oracle/clock dependencies.
- `placement_rescore_v11.py`: frozen rescoring algorithm; SHA af375557427fb3531d9250e682fe16da2e83d01cafa5249a91d67b058bddceba.
- `test_placement_v11_boundaries.py`: 9 logical regression checks, including ordering, debounce reset and final-placement retention. These are synthetic logic tests, not simulator admission.
- `bos_recording_io.py`: bounded RAM trace/HDF5 buffers; final large files are written sequentially to permitted BOS and SHA checked. No physics or control changes.

New large outputs: `/projects/a02012413/buckets/zenith-a02012413/liyufeng/safelab_mem0_five_seed_pro8_20261029/round7/`.
Small reports/configuration: `/project_a02012413/public/liyufeng/safelab_mem0_five_seed_pro8_20261029/eval_v1/round7/`.
