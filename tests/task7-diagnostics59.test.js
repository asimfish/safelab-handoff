'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const root='reports/task7-eval-v1-20261103/';
const read=p=>JSON.parse(fs.readFileSync(p));
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const s=read(root+'diagnostics59-qualifications-20261104.json');
test('59 strict-v1 diagnostics bind236 original SDK frames without enlarging the57-case placement rescore',()=>{
 const d=s.diagnostics;assert.equal(d.n,59);assert.equal(d.successes,3);assert.equal(d.SDK_frames,236);assert.equal(d.max_SDK_difference,0);assert.equal(d.formal,false);
 assert.equal(Object.values(d.per_variant).reduce((a,x)=>a+x.n,0),59);assert.equal(Object.values(d.per_variant).reduce((a,x)=>a+x.success,0),3);
 for(const v of Object.values(d.per_variant))assert.equal(Object.values(v.phase_hist).reduce((a,n)=>a+n,0),v.n);
 assert.equal(s.placement_CPU_rescore.n,57);assert.equal(s.placement_CPU_rescore.successes,3);assert.equal(s.placement_CPU_rescore.new_two_diagnostics_rescored,false);
 assert.equal(d.source.sha256,'6e944fe10bfc2343eb30a5d53b29fae6ac9fab036403d94e4995f2eb692e7ee1');
 assert.equal(digest(root+s.admission_components_unchanged.original_57_snapshot_report),s.admission_components_unchanged.original_57_snapshot_sha256);
});
test('four-lane and PCHIP preparation never grants scientific or formal qualification',()=>{
 assert.equal(s.independent_qualifications.length,2);
 for(const q of s.independent_qualifications){
  assert.equal(q.planned_GPUs,4);assert.equal(q.scientific_qualification_passed,false);assert.equal(q.stage_A_authorized,false);
  if(q.status==='CPU_passed_source_staging'){assert.equal(q.job_id,null);assert.equal(q.GPU_allocation_or_NN_running_claimed,false);assert.equal(q.actual_GPU_Apps,0);}
  if(q.official_status==='RUNNING'){assert.ok(q.job_id);assert.ok(q.actual_status_evidence);assert.ok(q.observed_at);}
 }
 const j=s.independent_qualifications.find(x=>x.kind==='PCHIP_expert_reconstruction');assert.equal(j.planned_expert_executions,8);assert.equal(j.models_called,0);
 const f=s.independent_qualifications.find(x=>x.kind==='four_lane_model_pool');assert.equal(f.logical_lanes_per_slot,4);assert.deepEqual(f.episodes,[0,1,50,51]);assert.equal(f.per_lane_natural_commit_requirement,3);assert.equal(f.prior_two_lane_qualification_not_inherited,true);assert.equal(f.ordinary_NN_attributes_all_immutable_claimed,false);
});
test('all12 formal rows remain0/null with executor and smoke gates closed',()=>{
 const rows=read('data.json').evaluations.filter(x=>x.id.startsWith('task7-eval-v11-A-original-'));assert.equal(rows.length,12);
 assert.equal(s.formal_trials_added,0);assert.equal(s.formal_success,null);assert.equal(s.stage_A_authorized,false);assert.equal(s.formal_rows_changed,false);
 for(const r of rows){assert.equal(r.trials,0);assert.equal(r.completed,0);assert.equal(r.success,null);assert.equal(r.evaluation_started,false);assert.equal(r.admission.executor_parity.passed,false);assert.equal(r.admission.smoke20.passed,false);}
 const summary='diagnostics59-qualifications-20261104.json';assert.equal(read(root+'diagnostic-progress.json').latest_59_qualification_snapshot.summary_sha256,digest(root+summary));
});
