'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const root='reports/task7-v12-relaxed-20261105/history_math/',read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),pub=read(root+'summary.json');
const cohorts=Object.fromEntries(Object.entries(pub.reports).map(([k,r])=>{assert.equal(sha(r.file),r.sha256);return[k,read(r.file)];}));
test('historical math remains an appendix with a frozen data snapshot and no new formal evaluation',()=>{
 assert.equal(pub.data_json_sha256,'2e4aa44b790b0bf649b53bab8d1451b443d3e34c65bb7344126e310fca263b48');
 const data=read('data.json');assert.equal(data.evaluations.find(r=>r.id==='task7-eval-v11-A-original-mem0_30k-h8').success,5);assert.equal(data.evaluations.find(r=>r.id==='task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8').success,7);
 assert.equal(pub.main_evaluation_rows_changed,false);assert.equal(pub.formal_score_eligible,false);assert.equal(pub.formal_placement_success,null);
 assert.equal(pub.actual_historical_cases,2385);assert.equal(pub.canonical_v11_U,2385);assert.equal(pub.canonical_relaxed_U,2385);
 assert.equal(pub.h30.historical_expected_n,1030);assert.equal(pub.h30.new_math_rescored_n,0);
 for(const r of Object.values(pub.sources))assert.equal(sha(r.file),r.sha256,r.file);
});
test('all2385 source projections preserve S F U, valid phase means and every stage without promoting math',()=>{
 const rows=pub.parts.flatMap(p=>{assert.equal(sha(p.file),p.sha256);const x=read(p.file).rows;assert.equal(x.length,p.rows);return x;});assert.equal(rows.length,2385);
 const seen=new Set();for(const r of rows){const key=[r.variant,r.horizon,r.condition,r.case_id].join('|');assert.ok(!seen.has(key));seen.add(key);assert.deepEqual(r.canonical_verdicts,{'v1.1':'U','v1.2-relaxed':'U'});assert.equal(r.formal_placement_success,null);assert.equal(r.strict_original.strict_reexecuted,false);assert.equal(r.training_resize_actual,null);}
 assert.equal(pub.groups.length,22);
 for(const g of pub.groups){
  const rr=rows.filter(r=>r.variant===g.variant&&r.checkpoint===g.checkpoint&&r.horizon===g.horizon&&r.condition===g.condition);assert.equal(rr.length,g.n_actual_historical_cases);
  assert.equal(g.canonical_placement_relaxed.U,rr.length);assert.equal(g.canonical_placement_relaxed.S,0);assert.equal(g.execution_and_preprocess_evidence.training_resize_actual,null);assert.equal(g.execution_and_preprocess_evidence.completionfix_actual,null);
  for(const name of ['v1.1','v1.2-relaxed']){
   const m=g.math[name],os=rr.map(r=>r.math_protocols[name]);assert.equal(m.S+m.F+m.U,rr.length);
   for(const v of ['S','F','U'])assert.equal(m[v],os.filter(o=>o.verdict===v).length);
   const known=os.filter(o=>o.verdict!=='U');assert.equal(m.mean_phase_n,known.length);assert.equal(Object.values(m.phase_hist_valid_closed_only).reduce((a,b)=>a+b,0),known.length);
   assert.equal(m.mean_phase_valid_closed_only,known.length?known.reduce((a,o)=>a+o.phase,0)/known.length:null);
   for(let k=1;k<=7;k++){const z=m.per_stage[k];assert.equal(z.S+z.F+z.U,rr.length);for(const v of ['S','F','U'])assert.equal(z[v],os.filter(o=>o.per_k[k]===v).length);}
  }
 }
});
test('legacy193missing plus25censored and oldP1 seed889 remain distinct from A739 canonical results',()=>{
 const legacy=cohorts['legacy-h4-h8-2265'],smoke=cohorts['old-smoke120'];assert.equal(legacy.actual_historical_n,2265);assert.equal(legacy.raw_full_SHA_CPU_verified_n,2072);assert.equal(smoke.raw_full_SHA_CPU_verified_n,120);
 const sum=(report,name)=>['S','F','U'].map(k=>report.groups.reduce((n,g)=>n+g.math[name][k],0));assert.deepEqual(sum(legacy,'v1.1'),[41,2031,193]);assert.deepEqual(sum(legacy,'v1.2-relaxed'),[48,1999,218]);
 const aligned=smoke.groups.find(g=>g.variant==='ours_aligned_30k');assert.deepEqual(['S','F','U'].map(k=>aligned.math['v1.2-relaxed'][k]),[4,15,1]);assert.equal(aligned.math['v1.2-relaxed'].complete_verdict_SR,null);
 assert.equal(aligned.math['v1.2-relaxed'].per_stage['4'].S,10);assert.equal(aligned.math['v1.2-relaxed'].per_stage['4'].U,1);
 assert.equal(smoke.groups.find(g=>g.variant==='mem0_30k').math['v1.2-relaxed'].S,2);
 assert.ok(smoke.groups.every(g=>g.execution_and_preprocess_evidence.execution_scope==='P1 original smoke chain'));
 assert.ok(pub.boundaries.some(x=>x.includes('seed889')&&x.includes('mainA739K')));
});
test('older original N1 completed100 matrices are distinct from the new formal notrun grid and assisted baseline8',()=>{
 const p=root+'old-original-N1-coverage-v1.json',c=read(p);assert.equal(sha(p),'d48f083e9f49e2413e14515adcebbd5a9e8ace416646e344fe401ed41ee2dc76');
 const q=c.scope.old_original_30k_h4_h8;assert.equal(q.historically_completed_reported,1000);assert.equal(q.complete_raw_index_obtained_n,0);assert.equal(q.included_current_2265,0);assert.equal(q.included_current_main200,0);assert.equal(q.included_current_smoke120,0);
 assert.equal(c.legacy_universe_verified.baseline,8);assert.equal(c.legacy_universe_verified.h4_h8_baseline,6);assert.equal(c.scope.additional_old_20k_h4_h8.historically_completed_reported,206);
 const mem=c.configurations.filter(r=>r.variant==='mem0_30k');assert.deepEqual(mem.map(r=>r.historical_success_original),[9,12]);assert.ok(mem.every(r=>r.new_formal_planned_notrun===false));
 const aligned=c.configurations.filter(r=>r.variant==='ours_aligned_loss_30k');assert.deepEqual(aligned.map(r=>r.historical_success_original),[4,7]);
 assert.equal(pub.additional_old_original_coverage.new_CPU_rescored_from_this_matrix_n,0);assert.equal(pub.additional_old_original_coverage.missing_index_is_not_proof_raw_lost,true);
});
