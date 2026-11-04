'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto'),M=require('../model');
const root='reports/task7-eval-v1-20261103/';
const read=p=>JSON.parse(fs.readFileSync(p));
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const s=read(root+'admission-components-20261104.json');
const rows=read('data.json').evaluations.filter(e=>e.id.startsWith('task7-eval-v11-A-original-'));

test('57 strict diagnostics conserve independent closure counts without becoming v1.1 trials',()=>{
 const d=s.diagnostics;assert.equal(d.protocol,'strict-v1');assert.equal(d.n,57);assert.equal(d.successes,3);assert.equal(d.SDK_frames,228);assert.equal(d.max_SDK_difference,0);
 assert.equal(Object.values(d.per_variant).reduce((a,x)=>a+x.n,0),57);
 assert.equal(Object.values(d.per_variant).reduce((a,x)=>a+x.success,0),3);
 for(const v of Object.values(d.per_variant))assert.equal(Object.values(v.phase_hist).reduce((a,n)=>a+n,0),v.n);
 assert.equal(s.placement_CPU_rescore.phase_changes,0);assert.equal(s.placement_CPU_rescore.success_changes,0);assert.equal(s.placement_CPU_rescore.original_execution_changed,false);
 assert.equal(d.formal,false);assert.equal(s.formal_trials_added,0);assert.equal(s.formal_success,null);
});

test('placement component acceptance binds the actual review without accepting the executor or StageA',()=>{
 const r=s.placement_oracle_component.root_review;assert.equal(digest(r.public_file),r.sha256);
 const review=read(r.public_file);assert.equal(review.expert_replay_component_passed,true);assert.equal(review.native_positive_episodes,10);assert.equal(review.negative_video_windows,30);
 assert.equal(review.initial_no_false_progression,true);assert.equal(review.execution_chain_differential_gate_passed,false);assert.equal(review.StageA_authorized,false);
 assert.equal(review.placement_oracle_sha256,'504d08fecd1859bd7b768759bc251f40f070ea404c8cac42ea29d508f5d66520');
});

test('render admission accepts the original comparison scope and keeps numerical residuals and old false records',()=>{
 const r=s.render_multiframe;assert.equal(digest(r.root_review.public_file),r.root_review.sha256);assert.equal(digest(r.evidence.public_file),r.evidence.sha256);
 const review=read(r.root_review.public_file),evidence=read(r.evidence.public_file);assert.equal(review.accepted_component_admission,true);assert.equal(review.StageA_authorized,false);
 assert.equal(r.passed,true);assert.equal(r.status,'required_multiframe_comparison_completed_residuals_retained');assert.equal(r.training_numeric_MAE_limit_in_standard,null);
 assert.equal(r.bitwise_render_identity,false);assert.equal(r.full_pipeline_equivalence_proven,false);assert.equal(r.input_cause_of_low_SR_excluded,false);
 const values=evidence.holdout_statistics.per_episode.flatMap(x=>x.five_point_MAE);assert.equal(values.length,40);assert.equal(Math.min(...values),r.raw_MAE_range_0_255[0]);assert.equal(Math.max(...values),r.raw_MAE_range_0_255[1]);assert.ok(values.every(v=>v>1));
 assert.equal(digest(root+'native-admission.json'),'f8514bcff5d26e5adddfc698cce9462ef6663081659eb1b43adcc5b9a68e16d5');assert.equal(read(root+'native-admission.json').passed,false);
});

test('complete10 success-count gate cannot hide RMSE failure or manufacture four original archive receipts',()=>{
 const e=s.executor_parity;assert.equal(e.complete_10_pairs,true);assert.equal(e.native_successes,10);assert.equal(e.endpoint_successes,9);assert.equal(e.success_count_gate_passed,true);
 assert.equal(e.passed,false);assert.equal(e.status,'failed_complete10_RMSE');assert.equal(e.pairs.length,10);assert.ok(e.pairs.every(p=>p.q13_RMSE_rad>e.limit_rad&&p.RMSE_passed===false));
 const actual=Math.sqrt(e.pairs.reduce((a,p)=>a+p.squared_error_sum,0)/e.pairs.reduce((a,p)=>a+p.physics_rows*13,0));assert.ok(Math.abs(actual-e.q13_RMSE_rad)<1e-14);
 assert.equal(e.archival.original_archive_receipt_case_count,16);assert.equal(e.archival.original_archive_receipt_missing_case_count,4);assert.equal(e.archival.all_original_archival_records_complete,false);
 assert.equal(e.retrospective_cases.length,4);assert.ok(e.retrospective_cases.every(p=>p.original_FINAL_ARCHIVE_present===false&&p.not_original_archive_receipt&&p.current_independent_listed_artifacts_verified));
});

test('ten untested rows stay empty; the historical weak review does not grant their hard gates',()=>{
  assert.equal(rows.length,12);assert.equal(s.stage_A_authorized,false);
  const pending=rows.filter(e=>!['task7-eval-v11-A-original-mem0_30k-h8','task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8'].includes(e.id));
  assert.equal(pending.length,10);
  for(const e of pending){
  assert.equal(e.trials,0);assert.equal(e.completed,0);assert.equal(e.success,null);assert.equal(e.evaluation_started,false);assert.equal(e.mean_phase,null);assert.deepEqual(e.phase_hist,{});
  assert.equal(e.scene_list_hash,'sha256:f6d728df04ff3d87927700173aa7f83c5ffa5de699d750f6da819e97156fae6f');
  assert.equal(e.admission.expert_replay.passed,true);assert.equal(e.admission.render_multiframe.passed,true);assert.equal(e.admission.executor_parity.passed,false);assert.equal(e.admission.smoke20.passed,false);
  assert.ok(M.formalIssues(e).includes('准入证据缺失'));assert.ok(M.formalIssues(e).includes('未完成或分母无效'));
  if(e.variant.includes('weak')){
   const gate=e.admission.open_loop,sha='7acc8df00014832b35e6b98741d8c21913de2053f6dcbcb2123354613127042f';
   assert.equal(gate.passed,true);assert.equal(gate.status,'passed_fixed10_fullmemory_relative_RMSE_rule_own_input_review');
   assert.equal(gate.evidence_sha256,sha);assert.equal(digest(gate.evidence_file),sha);assert.equal(digest(gate.own_parquet_audit_file),sha);
   const review=read(gate.evidence_file),sourceVariant={mem0_weak_30k:'mem0_weak_30k',ttc_weak_aligned_30k:'ours_weak_aligned_30k'}[e.variant];
   assert.ok(sourceVariant);const own=review.models.find(m=>m.variant===sourceVariant);assert.ok(own);
   assert.equal(review.actual_original_files_SHA_verified,14);assert.equal(review.actual_rows_compared,22817);assert.equal(review.actual_queries,210);
   assert.equal(review.field_match,255);assert.equal(review.field_mismatch,0);assert.equal(review.field_unknown,0);
   assert.equal(review.norm_raw_SHA_equal,false);assert.equal(review.norm_normalization_values_bitwise_equal,true);
   assert.equal(own.own_fixed10_parquet_input_gap_closed,true);assert.equal(own.relative_RMSE_rule_passed,true);assert.ok(own.ratio_to_Mem0<=1.5);
   assert.equal(review.hard_admission_granted,false);assert.equal(review.formal_StageA_cases_added,0);
   assert.equal(gate.prior_review.passed,false);assert.equal(gate.prior_review.status,'pending_own_converted_parquet');
   assert.equal(digest(gate.prior_review.own_parquet_audit_file),gate.prior_review.own_parquet_audit_sha256);
  }
 }
});

test('expert infrastructure terminal and recorded utilization do not imply model failure or continuous lifecycle coverage',()=>{
 const t=s.expert_job_terminal,u=s.expert_GPU_utilization;assert.equal(t.official_status,'FAILED');assert.equal(t.model_failures_added,0);assert.equal(t.actual_GPU_Apps,0);assert.equal(t.released_GPUs,4);assert.equal(t.reserved_GPUs,0);
 assert.equal(t.all20_owned_Native_positive_closed,true);assert.equal(t.sampler_scope_positive_closed,true);
 assert.ok(u.recorded_span_seconds>=2400);assert.ok(u.first600_percent<80&&u.last600_percent<80&&u.whole_recorded_span_percent<80);assert.equal(u.whole_provider_job_span_coverage_claimed,false);assert.ok(u.unrecorded_prefix_since_official_created_s>0&&u.unrecorded_tail_until_official_ended_s>0);
 assert.equal(s.causal_successor_snapshot.running_claimed,false);assert.equal(s.causal_successor_snapshot.new_job_POSTs_reported,0);
});
