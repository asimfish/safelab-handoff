'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto'),M=require('../model');
const root='reports/task7-eval-v1-20261103/',read=n=>JSON.parse(fs.readFileSync(n)),sha=n=>crypto.createHash('sha256').update(fs.readFileSync(n)).digest('hex');
const data=read('data.json'),summary=read(root+'codec40-and-abc20-final-20261105.json'),paired=read(root+'codec40-paired-statistics-20261105.json');
const variants=['mem0_30k','ours_aligned_30k'],ids=variants.map(v=>'task7-eval-v11-diagnostic-codecB0-'+v+'-h8-20261105');

test('codec40 adds only two diagnostic conditions and computes Wilson independently of bootstrap',()=>{
 const formal=M.formalComparisons(M.buildBoard(data),'placement-v1.1');
 for(const [i,id]of ids.entries()){
  const e=data.evaluations.find(e=>e.id===id),source=paired.variants[variants[i]].codec;
  assert.ok(e);assert.equal(e.record,i?'7-aligned':'7-mem0');assert.equal(e.handoff_issue,i?41:39);
  assert.equal(e.stage,'diagnostic');assert.equal(e.condition_version,'original-v1-codecB0-x264165-v1');
  assert.equal(e.formal_score_eligible,false);assert.equal(e.counts_toward_Stage_A,false);
  assert.equal(Object.hasOwn(e,'source_evaluation_id'),false);assert.equal(Object.hasOwn(e,'admission'),false);
  assert.ok(e.paired_baseline_evaluation_id.startsWith('task7-eval-v11-A-original-'));
  assert.equal(e.trials,20);assert.equal(e.completed,20);assert.equal(e.success+e.failure+e.unknown,20);
  assert.deepEqual(e.wilson95,M.wilson95(i?1:0,20));assert.ok(e.wilson95.high>0);
  assert.deepEqual(e.success_bootstrap_CI95,source.scores.placement.primary.CI95);
  assert.notDeepEqual([e.wilson95.low,e.wilson95.high],e.success_bootstrap_CI95);
  assert.equal(Object.values(e.phase_hist).reduce((a,b)=>a+b,0),20);
  assert.equal(e.mean_phase,Object.entries(e.phase_hist).reduce((a,[k,v])=>a+Number(k)*v,0)/20);
  assert.equal(e.lr_split.left.success+e.lr_split.right.success,e.success);
  assert.ok(!formal.some(r=>r.id===id));
 }
 assert.equal(data.evaluations.find(e=>e.id==='task7-eval-v11-A-original-mem0_30k-h8').success,5);
 assert.equal(data.evaluations.find(e=>e.id==='task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8').success,7);
});

test('codec paired results preserve censoring, original masks and non-improvement intervals',()=>{
 assert.equal(sha(root+'codec40-paired-statistics-20261105.json'),'85f020be251a4a58e3b7516046f9f9b4cc385538e82d25fe7bc07a3129eca174');
 assert.equal(sha(root+'codec40-verified-closure-index-20261105.json'),'4f70e45eff955432c0cc95b409f69dba08f80cb10a40ca7db9b972dc879d0730');
 assert.equal(paired.bootstrap.seed,20261105);assert.equal(paired.bootstrap.replicates,10000);
 for(const [i,varname]of variants.entries()){
  const p=paired.variants[varname],e=data.evaluations.find(e=>e.id===ids[i]);
  assert.deepEqual([p.baseline.scores.placement.primary.S,p.codec.scores.placement.primary.S],i?[2,1]:[1,0]);
  assert.equal(p.baseline.scores.strict.primary.U,i?2:1);assert.equal(p.baseline.scores.strict.primary.success_rate,null);
  assert.deepEqual([e.oracle_comparison.strict.success,e.oracle_comparison.strict.failure,e.oracle_comparison.strict.unknown],i?[0,19,1]:[0,20,0]);
  assert.equal(e.oracle_comparison.strict.complete_verdict_success_rate,i?null:0);
  const ci=p.paired_codec_minus_main.placement_mean_phase_CI95;assert.ok(ci[0]<0&&ci[1]>0);
  assert.equal(p.baseline.scores.placement.inclusive.S,0);assert.equal(p.codec.scores.placement.inclusive.S,i?1:0);
  assert.equal(p.codec.final_infra_unknown_n,0);assert.equal(p.codec.ever_unknown.runtime,i?2:0);
 }
});

test('ABC coverage, finite-prefix boundaries and incomplete journal remain explicit',()=>{
 for(const s of Object.values(summary.sources))assert.equal(sha(s.file),s.sha256,s.file);
 for(const varname of variants){
  const m=read(root+'abc20-'+varname+'-all-trim-tail-20261105.json');
  assert.equal(m.n_episodes,20);assert.equal(m.frames,8380);assert.deepEqual(m.n_by_order,{'1234':10,'4321':10});
  assert.equal(m.source_original_sha256,'3659344159bdfd74acd7652e80a08fe3d8c65500310242f6c2f3b56a2638cbe9');
  assert.equal(m.bootstrap.replicates,10000);assert.equal(m.bootstrap.seed,20261105);
  for(const scope of ['all','trim_last40','tail40']){
   assert.equal(m.scopes[scope].all.image.B_vs_C.MAE_0_255,null);
   for(const group of ['approach','close','transport','unknown'])assert.ok(m.scopes[scope][group]);
  }
 }
 assert.equal(summary.condition_boundaries.same_bitstream,false);assert.equal(summary.condition_boundaries.B_three_tick_exposure_state_confound,true);
 assert.equal(summary.archive.status,'archive_pending');assert.equal(summary.archive.journal_rejections,22);
 assert.equal(summary.archive.closed_verified_objects,1936);assert.equal(summary.archive.upload_pending,0);
 assert.equal(summary.archive.rejected_file_names_and_SHA,'unknown');
 assert.equal(summary.resource.allocated_GPU,0);assert.equal(summary.resource.steady_600s_target80_passed,false);
 assert.equal(summary.P1.native_expert_q13_RMSE_rad>.005,true);assert.equal(summary.P1.scores.placement.success,4);
 assert.equal(summary.formal_main_changed,false);
});
