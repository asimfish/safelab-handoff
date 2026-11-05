'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const root='reports/task7-eval-v1-20261103/';
const read=p=>JSON.parse(fs.readFileSync(p));
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const s=read(root+'pchip-final-and-fourlane-snapshot-20261104.json');
test('eight successful experts retain failing PCHIP trajectory parity and no selected formal chain',()=>{
 const j=s.PCHIP_expert_diagnostic;
 assert.equal(j.expert_executions,8);assert.equal(j.physical_success_count,8);assert.equal(j.model_calls,0);
 assert.equal(j.actual_valid_ticks_per_method,72883);assert.equal(j.original_RMSE_limit_rad,.005);
 assert.deepEqual(j.individual_RMSE_passes,[{method:'shape_preserving_direct8',episode:50}]);assert.equal(j.individual_RMSE_failures,7);
 for(const method of Object.values(j.methods)){assert.ok(method.original_native.all13.RMSE_rad>.005);assert.equal(method.method_qualified,false);assert.equal(method.all_four_individual_005_passed,false);}
 assert.equal(j.all_eight_raw_SDK_commands_match_frozen_CPU_expected,true);
 for(const k of ['winner_selected','full_ten_EP_gate_passed','execution_chain_admitted','all_lifecycle_and_full_archive_custody_verified'])assert.equal(j[k],false);
 assert.equal(j.incomplete_actual_GPU_lifecycle_supplement_rows.length,5);
 assert.equal(j.official_terminal.status,'SUCCEEDED');assert.equal(j.official_terminal.reserved_GPUs,0);assert.equal(j.official_terminal.released_GPUs,4);
 assert.equal(digest(root+j.published_original_math),j.math_source.sha256);assert.equal(j.math_source.sha256,'3001fc067978106c23977c9e3884ac24c0f845ad366627110e0d0f7673b50c0c');
});
test('fourlane frozen progress distinguishes eight parent closures from seven full RESULT mirrors',()=>{
 const f=s.four_lane_pool_snapshot;
 assert.equal(f.epoch,1793767244.6744008);assert.equal(f.source.sha256,'107bce95fa1721d6eb0cc3bc8872020fb2c39d99d83365f746fe0ff07e55ebdd');
 assert.equal(f.input_CPU.decoded_frames,9113);assert.equal(f.input_CPU.pixel_checks,84);assert.equal(f.input_CPU.maximum_pixel_difference,0);
 assert.deepEqual(f.parent_reported_cold_closed_counts_by_GPU,[3,2,2,1]);assert.equal(f.parent_reported_cold_closed_total,8);
 assert.equal(f.independently_read_complete_RESULT_mirrors,7);assert.equal(f.cold_RESULT_mirrors.length,7);
 assert.equal(new Set(f.cold_RESULT_mirrors.map(r=>`${r.GPU}/${r.lane}`)).size,7);
 for(const r of f.cold_RESULT_mirrors){assert.equal(r.natural_commits,3);assert.equal(r.positive_cleanup,true);}
 assert.equal(f.complete_pooled_RESULTS,0);assert.equal(f.actual_concurrent_policy_count,null);
 for(const k of ['whole_archive_custody_verified','four_lane_GPU_qualification_passed','prior_two_lane_qualification_inherited','physical_chain_qualification_inferred','ordinary_NN_attributes_all_immutable_claimed'])assert.equal(f[k],false);
});
test('J expert success and model bridge CPU tests cannot change formal model results or old snapshots',()=>{
 assert.equal(s.prior_59_diagnostic_snapshot.diagnostic_closed,59);assert.equal(s.prior_59_diagnostic_snapshot.diagnostic_successes,3);
 assert.equal(s.prior_59_diagnostic_snapshot.placement_CPU_rescored,57);assert.equal(s.prior_59_diagnostic_snapshot.new_two_placement_rescores_claimed,false);
 assert.equal(digest(root+s.prior_59_diagnostic_snapshot.report),s.prior_59_diagnostic_snapshot.sha256);
 assert.equal(s.model_bridge_v2_CPU_only.tests,28);assert.equal(s.model_bridge_v2_CPU_only.Native_or_NN_calls,0);assert.equal(s.model_bridge_v2_CPU_only.physical_or_NN_admission,false);
 assert.equal(s.formal_trials_added,0);assert.equal(s.formal_success,null);assert.equal(s.StageA_authorized,false);
 const rows=read('data.json').evaluations.filter(r=>r.id.startsWith('task7-eval-v11-A-original-'));assert.equal(rows.length,12);
 for(const r of rows){assert.equal(r.trials,0);assert.equal(r.completed,0);assert.equal(r.success,null);assert.equal(r.evaluation_started,false);assert.equal(r.admission.executor_parity.passed,false);assert.equal(r.admission.smoke20.passed,false);}
 assert.equal(s.resource_snapshot.total_reserved_GPUs,8);assert.equal(s.resource_snapshot.not_a_live_global_poll,true);
 const p=read(root+'diagnostic-progress.json');assert.equal(p.latest_PCHIP_final_and_F4_snapshot.summary_sha256,digest(root+'pchip-final-and-fourlane-snapshot-20261104.json'));
});
