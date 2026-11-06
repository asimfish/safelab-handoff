'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto'),M=require('../model'),zlib=require('node:zlib');
const path='reports/task7-v12-relaxed-20261105/',read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const data=read('data.json'),pub=read(path+'summary.json'),stats=read(path+'three-oracle-statistics.json'),parts=read(path+'record-parts.json');
const rows=parts.parts.flatMap(p=>{assert.equal(sha(p.file),p.sha256);return read(p.file).records;});
const variants=['mem0_30k','ours_aligned_30k'];
test('relaxed creates two diagnostic identities while original formal counts and protocol remain intact',()=>{
 assert.equal(M.CURRENT_PROTOCOL,'SafeLab-Eval-v1.1');assert.equal(rows.length,200);assert.equal(new Set(rows.map(x=>x.case_id)).size,200);
 for(const [i,v]of variants.entries()){
  const e=data.evaluations.find(x=>x.id===pub.new_evaluation_ids[i]);assert.ok(e);assert.equal(e.variant,v);
  assert.equal(e.protocol_version,'SafeLab-Eval-v1.2-relaxed');assert.equal(e.oracle_version,'placement-v1.2-relaxed');
  assert.equal(e.stage,'diagnostic');assert.equal(e.metric_role,'offline_rescore_v1_2_relaxed');assert.equal(e.formal_score_eligible,false);
  assert.equal(e.formal_admission_granted,false);assert.equal(e.qualification.passed,false);assert.equal(Object.hasOwn(e,'admission'),false);
  assert.equal(e.new_physical_trials,0);assert.equal(e.new_model_calls,0);assert.equal(e.source_original_stopping_extended,false);
  assert.deepEqual([e.success,e.failure,e.unknown],i?[11,83,6]:[5,95,0]);assert.equal(e.trials,100);
  assert.deepEqual(e.wilson95,M.wilson95(e.success,100));assert.equal(e.valid_verdict_n,i?94:100);
  assert.equal(e.success_rate,i?null:.05);assert.deepEqual(e.success_rate_identification_bounds,i?[.11,.17]:[.05,.05]);
  assert.equal(Object.values(e.phase_hist).reduce((a,b)=>a+b,0),i?94:100);
  assert.equal(e.mean_phase,Object.entries(e.phase_hist).reduce((a,[p,n])=>a+Number(p)*n,0)/e.phase_mean_denominator);
  const old=data.evaluations.find(x=>x.id===e.source_evaluation_id);assert.equal(old.success,i?7:5);assert.equal(e.condition,old.condition);assert.equal(e.condition_version,old.condition_version);
  assert.equal(M.formalComparisons(M.buildBoard(data)).some(x=>x.id===e.id),false);
 }
});
test('all seven prefix stages explicitly conserve S F U and retain censored observed reaches',()=>{
 for(const v of variants)for(const name of ['strict','v1.1','relaxed']){
  const rr=rows.filter(r=>r.configuration_id===v),o=stats.configurations[v].oracles[name];
  assert.deepEqual(Object.keys(o.per_k),['1','2','3','4','5','6','7']);
  for(const k of Object.keys(o.per_k)){
   const s=o.per_k[k];assert.equal(s.S+s.F+s.U,100);assert.equal(s.total_n,100);
   for(const verdict of ['S','F','U'])assert.equal(s[verdict],rr.filter(r=>r.oracles[name].per_k[k]===verdict).length);
  }
 }
 const t=stats.configurations.ours_aligned_30k.oracles.relaxed;
 assert.deepEqual([1,4,6,7].map(k=>[t.per_k[k].S,t.per_k[k].U]),[[91,1],[38,4],[16,5],[11,6]]);
 assert.equal(t.phase_known_n,99);assert.equal(t.phase_mean_denominator,94);
 const missing=rows.filter(r=>!r.raw_available);assert.equal(missing.length,1);
 for(const o of Object.values(missing[0].oracles)){assert.equal(o.phase,null);assert.equal(o.success,null);assert.deepEqual([...new Set(Object.values(o.per_k))],['U']);}
});
test('censored paired success is bounded rather than declared a known zero or full-cohort SR improvement',()=>{
 const p=stats.pairs[0];assert.equal(p.matched_identity_n,100);assert.equal(p.bootstrap.replicates,10000);assert.equal(p.bootstrap.seed,20261105);
 const strict=p.oracles.strict;assert.equal(strict.whole_unknown_pair_n,13);assert.equal(strict.whole_SR_difference,null);
 assert.deepEqual(strict.whole_SR_difference_identification_bounds,[-.05,.08]);
 assert.equal(strict.whole_SR_total_pair_difference,0);assert.deepEqual(strict.whole_SR_bootstrap.CI95,[0,0]);
 assert.ok(strict.whole_SR_total_pair_metric_role.includes('sensitivity'));assert.equal(strict.whole_SR_complete_case.paired_n,87);
 const relaxed=p.oracles.relaxed;assert.equal(relaxed.phase_paired_n,94);assert.equal(relaxed.phase_unknown_pair_n,6);
 assert.equal(relaxed.whole_SR_difference,null);assert.deepEqual(relaxed.whole_SR_difference_identification_bounds,[.06,.12]);
 assert.ok(relaxed.phase_difference_bootstrap.CI95[0]<0&&relaxed.phase_difference_bootstrap.CI95[1]>0);
 assert.equal(relaxed.whole_SR_complete_case.paired_n,94);assert.equal(relaxed.whole_SR_complete_case.unknown_pair_n,6);
});
test('relaxed source pins and qualification limits never promote legacy contact math or expert RMSE',()=>{
 for(const r of Object.values(pub.sources))assert.equal(sha(r.file),r.sha256,r.file);
 assert.equal(crypto.createHash('sha256').update(zlib.gunzipSync(fs.readFileSync(path+'oracle_relaxed.py.gz'))).digest('hex'),'ead111d6deac265578f9015c65ef8f8b371127583fb2f9f0ccdc0a2c7339c674');
 assert.equal(sha(path+'qualification-v4.json'),'aed9a53728e35450263f2a850f9a6a7a2f6aa71a2a9739a6e99b7e50452ec5d4');
 assert.equal(pub.qualification.passed,false);assert.equal(pub.qualification.expert_E.unique_raw_SHA,3);
 assert.equal(pub.historical_coverage.canonical_relaxed_U,3295);assert.equal(pub.historical_coverage.canonical_v11_U,3295);
 assert.equal(pub.historical_coverage.new_historical_math_started,false);assert.equal(pub.formal_score_eligible,false);
 assert.equal(pub.actual_raw_CPU_SHA_verified,199);assert.equal(pub.missing_original_raw,1);
 const grid=read(path+'formal12-planned-vs-archived-grid.json');assert.equal(grid.rows.length,12);assert.equal(grid.notrun_grid_n,10);assert.equal(grid.actual_archived_grid_n,2);
 assert.equal(grid.rows.reduce((n,r)=>n+r.actual_same_chain_archived_case_n,0),200);assert.equal(pub.formal12_coverage.no_fabricated_1000_unknown_cases,true);
});
