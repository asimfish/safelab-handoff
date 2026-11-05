'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const path='reports/task7-eval-v1-20261103/diagnostic-progress.json';
const raw=fs.readFileSync(path),report=JSON.parse(raw);

test('latest task7 diagnostics add no formal results or admission',()=>{
 assert.equal(report.role,'diagnostic_only_not_admission');
 assert.equal(report.formal_stage_A_trials_added,0);assert.equal(report.formal_success,null);
 assert.equal(report.admission_granted,false);assert.equal(report.formal_rows_changed,false);
 assert.equal(report.frozen_scene_list_changed,false);
 const inventory=JSON.parse(fs.readFileSync('reports/task7-eval-v1-20261103.json'));
 assert.equal(inventory.latest_diagnostic_progress.summary_sha256,crypto.createHash('sha256').update(raw).digest('hex'));
 assert.equal(report.publication_boundary.base64_or_raw_image_trace_payloads_included,false);
 assert.equal(report.publication_boundary.previous_raw_action_diagnostic_and_missing12_raw_history_unchanged,true);
});

test('correct interval-end world0 replays retain independent diagnostic and render-failure scope',()=>{
 const replay=report.correct_target_world0_replay;
 assert.equal(replay.actual_training_loader_converted_targets_used,true);assert.equal(replay.raw_action_used_as_label,false);
 assert.deepEqual(replay.episodes.map(x=>[x.episode,x.frames,x.physical_phases]),[[0,2227,7],[50,2341,7]]);
 assert.ok(replay.episodes.every(x=>x.physical_success&&x.exact_scope_cleanup_passed));
 assert.equal(replay.archive_verified,true);assert.equal(replay.raw_trace_rehashed_in_final_capture,false);
 assert.equal(replay.raw_trace_hashes_verified_by_original_publication,true);
 assert.equal(replay.original_fixed100_cohort_expert_admission_promoted,false);
 assert.equal(report.render.passed,false);assert.equal(report.render.threshold_changed,false);
 for(const kind of ['raw640_rows','actual_training224_rows']){
  const values=report.render[kind].flatMap(x=>x.MAE_0_255);assert.equal(values.length,10);
  assert.ok(values.every(x=>x>report.render.declared_limit_MAE_0_255));
 }
});

test('five measured sparse model errors do not qualify FIFO30, Gen, or formal closed loop',()=>{
 const diag=report.pure_model_sparse210;
 assert.equal(diag.models.length,5);assert.equal(diag.official_status,'SUCCEEDED');
 assert.equal(diag.low_priority_GPUs_released,4);assert.equal(diag.scored,false);
 assert.equal(diag.closed_loop_cases,0);assert.equal(diag.formal_cases,0);
 assert.equal(diag.soft_admission_verified,false);assert.equal(diag.full_training_FIFO30_reproduced,false);
 assert.equal(diag.Gen_or_Planner_tested,false);assert.equal(diag.weak_direct_converted_parquet_limitation_preserved,true);
 for(const row of diag.models){assert.equal(row.observations,210);assert.equal(row.valid_arm_values,44100);assert.ok(row.ratio_to_Mem0base<=1.12);assert.ok(row.cleanup_passed&&row.archive_verified);}
 for(const row of diag.models.filter(x=>x.variant.startsWith('ours_'))){assert.equal(row.actual_KF_DAG_labels_replayed,true);}
 for(const row of diag.models.filter(x=>x.variant.includes('weak'))){assert.equal(row.actual_own_language_replayed,true);assert.equal(row.weak_converted_parquet_directly_read,false);}
 assert.equal(diag.utilization.required_600s_coverage_met,false);assert.ok(diag.utilization.measured_valid_seconds<600);
});

test('capture reference and image clock labels do not become a fabricated four-tick cause',()=>{
 const timing=report.timing_and_codec;
 assert.deepEqual([timing.capture_marker_tick_f0,timing.state_reference_tick_f0,timing.last_explicit_render_after_step_f0],[128,124,121]);
 assert.equal(timing.same_mapping_as_current_Native,true);assert.equal(timing.four_tick_bug_established,false);
 assert.equal(timing.codec_explains_all_render_error,false);assert.equal(timing.historical_dynamic_hooks_fully_recovered,false);
 assert.ok(timing.yuv420p_roundtrip_vs_training_MAE>1);
});

test('creation and memory snapshots remain time-bound risks without invented running Apps or freed cache',()=>{
 const smoke=report.smoke_creation_snapshot;
 assert.ok(smoke.observed_at.endsWith('Z'));assert.equal(smoke.create_HTTP_status,202);
 assert.equal(smoke.job_id,null);assert.equal(smoke.actual_Apps,0);assert.equal(smoke.reserved_GPUs,4);
 assert.equal(smoke.running_claimed,false);assert.equal(smoke.ongoing_liveness_claimed,false);
 const mem=report.Pro_memory_risk_snapshot;
 assert.ok(mem.shmem_bytes_subset_of_file<mem.file_bytes_including_shmem);
 assert.ok(mem.raw_headroom_bytes<64*2**30);assert.ok(mem.dev_shm_used_bytes<mem.dev_shm_size_bytes);
 assert.equal(mem.potential_is_not_released_or_admission_memory,true);
 assert.equal(mem.guard_lowered,false);assert.equal(mem.old_failures_root_cause_claimed,false);
 assert.equal(mem.native_shadow_model_started,false);
});

test('CPU candidates cannot stand in for GPU pool or native-head switch qualification',()=>{
 const shadow=report.candidates_only.native_head_shadow,pool=report.candidates_only.online_pool_guard;
 assert.equal(shadow.CPU_tests_passed,10);assert.equal(pool.CPU_tests_passed,23);
 assert.equal(shadow.GPU_tested,false);assert.equal(pool.GPU_tested,false);
 assert.equal(shadow.native_head_controls_current_online_switch,false);
 assert.equal(shadow.explicit_new_variant_needed_for_native_head_switch,true);
 assert.equal(pool.old_TTC_training_fixture_cannot_enable_pool,true);
 assert.equal(pool.existing_sealed_services_changed,false);
 for(const file of ['reports/task7-eval-v1-20261103.html','reports/task7-eval-v1-20261103/native-admission.html'])assert.ok(fs.readFileSync(file,'utf8').includes('diagnostic-progress.html'));
});
