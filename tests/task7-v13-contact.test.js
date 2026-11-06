'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto'),M=require('../model');
const root='reports/task7-v13-contact-20261106/',read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const data=read('data.json'),pub=read(root+'PUBLICATION.json'),stats=read(root+'FIRST_FOUR_PROTOCOL_TABLE.json'),validation=read(root+'VALIDATION.json');
test('task7 contact-authoritative v1.3 stays separate from seven ordered subtasks and the v1.1 main table',()=>{
 assert.equal(M.CURRENT_PROTOCOL,'SafeLab-Eval-v1.1');assert.equal(pub.new_v13_ids.length,4);
 const board=M.buildBoard(data),formal=M.formalComparisons(board);
 for(const id of pub.new_v13_ids){
  const e=data.evaluations.find(r=>r.id===id);assert.ok(e);assert.equal(e.protocol_version,'SafeLab-Eval-v1.3-lenient');
  assert.equal(e.stage,'diagnostic');assert.equal(e.formal_score_eligible,false);assert.equal(e.total_stages,4);assert.equal(e.half_task_k,2);
  assert.equal(e.new_physical_trials,0);assert.equal(e.new_model_calls,0);assert.equal(e.source_original_stopping_extended,false);
  const source=data.evaluations.find(r=>r.id===e.source_evaluation_id);assert.ok(source);assert.equal(source.record,e.record);assert.equal(source.checkpoint,e.checkpoint);assert.equal(source.horizon,e.horizon);
  assert.equal(formal.some(r=>r.id===e.id),false);assert.equal(e.success+e.failure+e.unknown,100);
  assert.equal(Object.values(e.phase_hist).reduce((a,b)=>a+b,0),100-e.unknown);
  assert.deepEqual(e.wilson95,M.wilson95(e.success,100));
 }
 assert.equal(data.evaluations.find(r=>r.id==='task7-eval-v11-A-original-mem0_30k-h8').success,5);
 assert.equal(data.evaluations.find(r=>r.id==='task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8').success,7);
});
test('all four-protocol results preserve full denominators, unknowns, stage units and valid-only means',()=>{
 for(const protocols of Object.values(stats.groups))for(const [protocol,o] of Object.entries(protocols)){
  assert.equal(o.N,100);assert.equal(o.success+o.failure+o.unknown,100);assert.equal(o.total_stages,protocol==='v1.3-lenient'?4:7);
  assert.equal(Object.values(o.phase_hist_valid).reduce((a,b)=>a+b,0),o.mean_phase_valid_n);
  assert.equal(o.mean_phase_valid_n,100-o.unknown);
  assert.equal(o.mean_phase,Object.entries(o.phase_hist_valid).reduce((n,[k,v])=>n+Number(k)*v,0)/o.mean_phase_valid_n);
  assert.equal(Object.keys(o.SR_at_k).length,o.total_stages);
  let previous=100;for(const k of Object.keys(o.SR_at_k)){
   const x=o.SR_at_k[k];assert.equal(x.S+x.F+x.U,100);assert.ok(x.S<=previous);previous=x.S;
  }
  assert.equal(o.half_task_k,Math.ceil(o.total_stages/2));assert.equal(o.half_task.S,o.SR_at_k[o.half_task_k].S);
  assert.equal(Object.values(o.left_right).reduce((n,x)=>n+x.U,0),o.unknown);
 }
 assert.equal(stats.groups.pi05_40k_h8['v1.3-lenient'].success_rate,null);
 assert.deepEqual(stats.groups.pi05_40k_h8['v1.3-lenient'].success_identification_bounds,[0,.14]);
 assert.equal(stats.groups.mem0_30k_h8.strict.success_rate,null);
});
test('the user-approved contact requirement rejects the original height-only false positives',()=>{
 const p=read(root+'FROZEN_PARAMETERS.json');assert.equal(p.height_fallback_used,false);assert.equal(p.height_proxy_cannot_override_measured_no_contact,true);
 assert.equal(p.N,4);assert.equal(p.effective_xy_tolerance_m,.06);assert.equal(p.initial_pad_credit,false);
 assert.equal(validation.expert_success,10);assert.equal(validation.expert_distinct_raw_sha,3);
 assert.deepEqual(validation.negative_counts,{airborne_above_target:5,hand_lifted_from_target:5,wrong_target:5});
 assert.equal(validation.negative_cases.length,15);assert.equal(validation.all_15_rejected,true);assert.equal(validation.start_pad_false_credit,0);
 let heightOnly=0;for(const c of validation.negative_cases){
  assert.equal(c.new_contact_predicate_passed,false);assert.match(c.window.sha256,/^[0-9a-f]{64}$/);assert.match(c.source_raw.sha256,/^[0-9a-f]{64}$/);
  if(c.literal_old_predicate_passed){heightOnly++;assert.equal(c.new_conditions.support_contact,false);assert.equal(c.new_conditions.height_supported,true);}
 }
 assert.equal(heightOnly,10);
 for(const [file,hash] of Object.entries(pub.source_files))assert.equal(sha(root+file),hash);
 assert.equal(sha(root+'oracle_v13.py'),'84da94e16d3290b869ef2f713dbdab96bc00169f682a33a4f0fa65502179080d');
});
test('paired success uncertainty cannot be converted into a significant TTC whole-task gain',()=>{
 const p=stats.paired_TTC_minus_Mem0['v1.3-lenient'];assert.equal(p.known_pairs,99);assert.equal(p.unknown_pairs,1);
 assert.ok(p.success_difference_bootstrap95_known_pairs[0]<0);assert.ok(p.success_difference_bootstrap95_known_pairs[1]>0);
 assert.deepEqual(p.full100_success_difference_identification_bounds,[.06,.07]);
 assert.ok(p.mean_phase_difference_bootstrap95[0]>0);
});
