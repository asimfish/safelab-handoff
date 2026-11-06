# Seven-task observation codec diagnostic

This document records the frozen comparison and its interpretation boundaries.
It is not a completed result report. Main-table placement results remain
Mem-0 30k h8 5/100 and TTC aligned 30k h8 7/100.

## Inputs and inference

A is decoded training video. B is the sealed
`B_recorded_obs_pose_render` image at the recorded observation pose. Offline C
is B after the recovered training H.264 codec round trip. The fixed episodes
are 0–9 and 50–59, 20 episodes and 8,380 queries per method: every first-subtask
query and 30 queries after the first switch. Both methods use their unchanged
training-side tensor bilinear resize with antialiasing.

For every image substitution, state, text, pre-query memory and inference noise
are held constant. A advances the chronological memory; B and C use disposable
forks. This measures current-image sensitivity, not separate B/C closed-loop
memory histories. Existing A outputs are reused only after exact first-episode
sampler verification; A forward calls still advance the original memory.

The deployment tensor audits passed on five fixed training frames for main
Mem-0 and TTC, including actual fixed-noise 30×13 model actions. The original
pi0.5 audit also passed and its source was reverified. These are bounded audit
results, not proof for every frame or every checkpoint variant.

## Recovered training codec and online exception

Actual source streams are 640×480, 15 Hz, H.264 High, yuv420p, CRF23,
keyint250/min-keyint15/scenecut40, B-frames3, rc-lookahead40. The recorded x264
core is 164 r3191 4613ac3. The original preset name is unavailable and is not
inferred. Training's lossless FFV1 cache preserves decoded H.264 artifacts.

Offline C retains the B-frame/lookahead settings and uses FFmpeg 7.0.2.
The current causal closed-loop condition is explicitly **codecB0**: one
persistent stream per lane/episode, B-frames0, lookahead0, zerolatency. Its
captured PyAV16/libavcodec62.11/x264core165 runtime differs from the source
encoder. It therefore approximates the codec domain under causal latency;
it is not a bit-exact implementation of the historical training stream.

The initial real closed-loop receipt verifies that raw Native RGB enters the
codec, current input/output PTS match, decoded RGB changes, and no bypass is
used. That receipt covers four frames of one lane; CPU tests separately cover
interleaved lanes and episode reset. It does not prove every lane by itself.

## Existing rendering and finite-prefix limitations

B uses recorded observation state at tick124+8i, while A's recorded image
exposure corresponds to tick121+8i. Original intermediate measured state and
complete rendering history are unavailable. Thus A/B is not a pure optical
intervention. The main rollout's derived render-tick metadata alone is not
proof of actual camera exposure timing.

Encoding the 432/406-query prefix also flushes without the remainder of the
original episode. Report all queries and, separately, the final40 and
trim-final40 sensitivity. A five-frame source-decoder crosscheck passed;
there is no claimed all-8,380-frame cross-decoder equivalence.

## Closed-loop cohort and statistics

Use the first20 original main-table scenes by frozen dispatch order,
10 order1234 and 10 order4321, for each method, h8. Scene IDs, seed, model,
K-cubic execution, time limit, physics and oracles are unchanged. The frozen
uncompressed references are Mem-0 1/20, mean phase2.45, and TTC 2/20,
mean phase3.25. The scene-list SHA is
`f6d728df04ff3d87927700173aa7f83c5ffa5de699d750f6da819e97156fae6f`.

Count the first valid original CPU/SDK closure. Infrastructure interruptions
get one same-seed queue-tail retry; an unclosed exhausted case is unknown in
the denominator20. Keep original strict/FD censored outcomes unknown, never
convert missing results to zero. Mean phase excludes final unknown cases;
paired mean uses only pairs with valid phase on both sides.

Use 10,000 shared paired bootstrap draws, seed20261105, stratified10+10 by
order. Open-loop resamples episode clusters and pools squared error/count
before the square root. Unknown-as-failure sensitivity uses the original
main-table inclusive startup-abort overlay plus runtime interruptions; show
runtime-only sensitivity separately. New codec cases receive no fabricated
historical startup-abort overlay.

All codec comparisons are `stage=diagnostic`. Final success rates and CIs
remain null until each fixed cohort is complete. Neither better image MAE nor
better open-loop RMSE alone establishes a closed-loop gain or authorizes v1.2.
