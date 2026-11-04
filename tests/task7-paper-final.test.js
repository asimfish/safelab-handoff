'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const M=require('../model.js');
const root='reports/task7-eval-v1-20261103/',read=n=>JSON.parse(fs.readFileSync(n)),sha=n=>crypto.createHash('sha256').update(fs.readFileSync(n)).digest('hex');
const data=read('data.json'),source=read(root+'paper-final-main-table-20261104.json');
const ids=['task7-eval-v11-A-original-mem0_30k-h8','task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8'];
const rows=ids.map(id=>data.evaluations.find(e=>e.id===id));

test('only the two root-adjudicated original h8 paper cells supply final task7 scores',()=>{
 assert.equal(sha(root+'paper-final-main-table-20261104.json'),'f94c4beed1895721a0523f4b4a0ffcec551f84759d1a161a7a10848ecf24462f');
 assert.equal(source.admission_status,'both_exact_paper_scopes_accepted_with_recorded_limitations');
 for(const [i,e] of rows.entries()){
  const s=source.rows[i];assert.equal(e.record,i?'7-aligned':'7-mem0');assert.equal(e.handoff_issue,s.record);
  assert.equal(e.protocol_version,'SafeLab-Eval-v1.1');assert.equal(e.oracle_version,'placement-v1.1');assert.equal(e.stage,'A');
  assert.equal(e.horizon,8);assert.equal(e.checkpoint,30000);assert.equal(e.condition_version,'original-v1');assert.equal(e.paper_cohort,'A739');
  assert.equal(e.completed,100);assert.equal(e.trials,100);assert.equal(e.evaluation_started,true);assert.equal(e.final_verified,true);
  assert.equal(e.success,s.success);assert.equal(e.failure,s.failure);assert.equal(e.unknown,s.unknown);assert.equal(e.success+e.failure+e.unknown,100);
  assert.deepEqual(M.formalIssues(e),[]);assert.equal(e.topology.num_envs_actual,1);assert.equal(e.topology.procs_per_gpu,4);
  assert.equal(e.topology.current_GPUs,0);assert.equal(e.topology.actual_Apps,0);assert.deepEqual(e.actual_world_origin,[0,0,0]);assert.equal(e.position_jitter_m,0);
 }
 const board=M.buildBoard(data),shown=M.formalComparisons(board,'placement-v1.1');
 for(const id of ids)assert.ok(shown.some(e=>e.id===id));
 const pending=data.evaluations.filter(e=>e.id.startsWith('task7-eval-v11-A-original-')&&!ids.includes(e.id));
 assert.equal(pending.length,10);assert.ok(pending.every(e=>e.trials===0&&e.success===null&&e.evaluation_started===false));
});

test('TTC retains one infrastructure unknown, exact positive2/reverse5 and known-only phase statistics',()=>{
 assert.deepEqual(rows.map(e=>[e.success,e.failure,e.unknown]),[[5,95,0],[7,92,1]]);
 assert.deepEqual(rows.map(e=>[e.lr_split.left.success,e.lr_split.right.success]),[[3,2],[2,5]]);
 assert.equal(rows[1].lr_split.right.unknown,1);assert.equal(rows[1].lr_split.right.failure,44);
 for(const [i,e] of rows.entries()){
  assert.equal(Object.values(e.phase_hist).reduce((a,b)=>a+b,0),e.trials-e.unknown);
  assert.equal(e.mean_phase,Object.entries(e.phase_hist).reduce((a,[k,v])=>a+Number(k)*v,0)/(e.trials-e.unknown));
  assert.equal(e.phase_mean_denominator,i?99:100);assert.equal(e.seed_results[0].inference_master_seed,739000);
  assert.equal(e.seed_results[0].success,e.success);assert.equal(e.seed_results[0].unknown,e.unknown);
  assert.equal(e.wilson95.low,M.wilson95(e.success,100).low);assert.equal(e.wilson95.high,M.wilson95(e.success,100).high);
 }
 assert.deepEqual(rows[0].phase_mean_bootstrap95,[2.01,2.77]);
 assert.deepEqual(rows[1].phase_mean_bootstrap95,[2.323232323232323,3.0606060606060606]);
 assert.deepEqual(rows[1].unknown_reasons,{infrastructure:1});
});

test('strict/FD censoring and inclusive sensitivity never become physical failures or complete known0percent',()=>{
 for(const [i,e] of rows.entries()){
  const s=i?{success:0,failure:92,unknown:8,censored:7}:{success:0,failure:95,unknown:5,censored:5};
  assert.deepEqual(e.oracle_comparison.strict,s);assert.deepEqual(e.oracle_comparison.strict_fdvel,s);
  assert.equal(e.oracle_comparison.complete_verdict_success_rate,null);assert.equal(e.oracle_comparison.censored_not_physical_failure,true);
 }
 assert.equal(source.rows[0].sensitivity.inclusive_ever_unknown_as_failure.S,3);
 assert.equal(source.rows[0].sensitivity.inclusive_ever_unknown_as_failure.mask_n,33);
 assert.equal(source.rows[1].sensitivity.inclusive.S,4);assert.equal(source.rows[1].sensitivity.counts.inclusive_union_n,47);
 assert.equal(source.rows[1].sensitivity.counts.runtime_mask_n+source.rows[1].sensitivity.counts.startup_mask_n-source.rows[1].sensitivity.counts.runtime_startup_overlap_n,47);
 const pair=source.paired_phase;assert.equal(pair.paired_n,99);assert.equal(pair.unknown_n,1);
 assert.equal(pair.mean_TTC_minus_Mem0_phase_known_pairs_only,0.30303030303030304);
 assert.ok(pair.conditional_paired_bootstrap_CI95[0]<0&&pair.conditional_paired_bootstrap_CI95[1]>0);
 assert.equal(pair.pairs.filter(p=>p.TTC_minus_Mem0_phase!=null).length,99);
 assert.equal(pair.pairs.filter(p=>p.TTC_minus_Mem0_phase==null).length,1);
});

test('new physical-rule acceptance keeps historical RMSE failure, render residuals and original admission flags',()=>{
 const reviewSHAs=['990debf59140f9be9d8142b10c5621b9a0539d4b3aae38712a0c971cc44674a1','6ce6878f65668665d914695efecdb66b2c9571a89ead8cf136938427c497a69f'];
 for(const [i,e] of rows.entries()){
  assert.equal(sha(e.root_admission_review.file),reviewSHAs[i]);assert.equal(e.root_admission_review.sha256,reviewSHAs[i]);
  for(const name of M.admissionKeys(e)){assert.equal(e.admission[name].passed,true);assert.equal(sha(e.admission[name].evidence_file),e.admission[name].evidence_sha256);}
  assert.equal(e.admission.executor_parity.historical_RMSE_passed,false);assert.ok(e.admission.executor_parity.historical_q13_RMSE_rad>.005);
  assert.equal(e.prior_admission_snapshot.executor_parity.passed,false);assert.equal(e.prior_admission_snapshot.smoke20.passed,false);
  assert.equal(e.admission.render_multiframe.bitwise_render_identity,false);assert.equal(e.admission.render_multiframe.full_pipeline_equivalence_proven,false);
  assert.equal(e.admission.render_multiframe.old_internal_1p0_false_preserved,true);assert.equal(e.admission.smoke20.duplicate_A_trials_added,0);
  assert.deepEqual(e.admission.smoke20.order_split,{'1234':10,'4321':10});assert.equal(e.admission.smoke20.phase0,i?2:1);
 }
 const ttc=read(root+'paper-final-ttc-admission-evidence-20261104.json');
 assert.equal(ttc.formal_admission_granted,false);assert.equal(ttc.raw_worker_scored_or_formal_fields_modified,false);
 assert.equal(sha(root+'paper-final-ttc-admission-evidence-20261104.json'),'705f19e55896c6e11c982b1392ccd43d4fabf9d6e0e751af4c80d8f38ee03dbb');
 assert.equal(ttc.preserved_limitations.old_q13_RMSE_passed,false);assert.equal(ttc.final_smoke20.valid,20);
});
