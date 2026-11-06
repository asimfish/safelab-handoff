'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model');
const read=p=>JSON.parse(fs.readFileSync(p));
const data=read('data.json'),r=read('reports/task7-three-seed-20261106/results.json');
test('task7 three-seed report binds698 raw traces, two unknown and all700 planned cases',()=>{
 assert.equal(r.raw_verified,698);assert.equal(r.planned,700);assert.equal(r.cases.length,700);
 assert.equal(new Set(r.cases.map(c=>c.case_id)).size,700);
 assert.equal(r.cases.filter(c=>c.raw_SHA_verified).length,698);
 assert.equal(r.complete_private_source.sha256,'ac7abf91af428dcc6a69888f33f54885931ce2c8f7b85b06c27ac73dff7c25a2');
 for(const row of r.rows){
  const cs=r.cases.filter(c=>c.variant===row.variant&&c.horizon===row.horizon&&c.seed_index===row.seed_index);
  assert.equal(cs.length,100);assert.equal(cs.filter(c=>c.order==='1234').length,50);
  for(const [p,s]of Object.entries(row.scores)){
   assert.equal(s.success+s.failure+s.unknown,100);
   assert.equal(cs.filter(c=>c.scores[p].verdict==='S').length,s.success);
   assert.equal(cs.filter(c=>c.scores[p].verdict==='U').length,s.unknown);
   assert.equal(Object.values(s.phase_hist).reduce((a,b)=>a+b,0),100-s.unknown);
   assert.equal(Object.entries(s.phase_hist).reduce((a,[k,v])=>a+Number(k)*v,0)/(100-s.unknown),s.mean_phase);
   assert.equal(s.N,p==='v1.3'?4:7);
  }
 }
});
test('new per-seed/h4 diagnostics have complete100 denominators and never replace main admission',()=>{
 const rows=data.evaluations.filter(e=>e.id.startsWith('task7-new-raw-'));
 assert.equal(rows.length,25);
 for(const e of rows){
  assert.equal(e.stage,'diagnostic');assert.equal(e.formal_score_eligible,false);
  assert.equal(e.trials,100);assert.equal(e.completed,100);assert.equal(e.success+e.failure+e.unknown,100);
  assert.equal(Object.values(e.phase_hist).reduce((a,b)=>a+b,0),100-e.unknown);
  assert.ok(M.formalIssues(e).length>0);
  if(e.oracle_version==='placement-v1.1'){assert.equal(e.source_evaluation_id,undefined);assert.ok(e.baseline_evaluation_id);}
  else assert.ok(rows.some(s=>s.id===e.source_evaluation_id&&s.horizon===e.horizon&&s.seed_index===e.seed_index&&s.record===e.record));
 }
 const h4=rows.find(e=>e.horizon===4&&e.oracle_version==='placement-v1.1');assert.equal(h4.success,10);assert.equal(h4.unknown,0);assert.equal(h4.mean_phase,2.82);
 const strict=rows.find(e=>e.horizon===4&&e.oracle_version==='strict-v1');assert.equal(strict.success,0);assert.equal(strict.unknown,10);assert.equal(strict.known_full_SR,null);
});
test('task7 requested500 progress remains unfinished and interval claims retain censoring',()=>{
 const rows=data.evaluations.filter(e=>e.id.startsWith('task7-v11-B-five-seed-progress-'));assert.equal(rows.length,2);
 for(const e of rows){assert.equal(e.trials,500);assert.equal(e.completed,300);assert.equal(e.success,null);assert.equal(e.final_verified,false);assert.equal(e.mean_phase,null);assert.ok(M.formalIssues(e).length>0);}
 const p=r.paired['v1.1'];assert.equal(p.success.planned_pairs,300);assert.equal(p.success.unknown_pairs,2);assert.equal(p.success.known_pairs,298);assert.ok(p.success.bootstrap95[0]<0&&p.success.bootstrap95[1]>0);
 const t=read('reports/task7-three-seed-20261106/timing-audit.json');
 for(const x of t.rows.filter(x=>x.grid==='policy_15Hz_rows'&&x.group==='all'))assert.deepEqual(x.minimum_shift,{all:0,arm:0,hand:0});
 assert.equal(t.target_contract.no_unrecorded_training_120Hz_state_claim,true);
});
