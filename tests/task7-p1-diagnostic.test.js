'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto'),M=require('../model');
const root='reports/task7-p1-diagnostic-20261105/',read=n=>JSON.parse(fs.readFileSync(n)),sha=n=>crypto.createHash('sha256').update(fs.readFileSync(n)).digest('hex');
const data=read('data.json'),id='task7-eval-v11-diagnostic-P1-linear8-mem0_30k-h8-20261105',e=data.evaluations.find(r=>r.id===id),s=read(root+'summary.json'),pairs=read(root+'PAIRED100.json');

test('P1 is an independent completed diagnostic, excluded from formal comparisons',()=>{
 assert.equal(e.record,'7-mem0');assert.equal(e.handoff_issue,39);assert.equal(e.variant,'mem0_30k');assert.equal(e.horizon,8);
 assert.equal(e.stage,'diagnostic');assert.equal(e.oracle_version,'placement-v1.1');assert.equal(e.condition_version,'original-v1-P1-linear8-arm7cap3p14-handFF0-v1');
 assert.deepEqual([e.success,e.failure,e.unknown,e.trials],[4,96,0,100]);assert.equal(e.mean_phase,2.6);assert.equal(e.phase_mean_denominator,100);
 assert.deepEqual(e.wilson95,M.wilson95(4,100));assert.deepEqual(e.phase_mean_bootstrap95,[2.22,3.01]);
 assert.equal(e.formal_score_eligible,false);assert.equal(e.formal_admission_granted,false);assert.equal(e.counts_toward_Stage_A,false);
 assert.equal(Object.hasOwn(e,'source_evaluation_id'),false);assert.equal(Object.hasOwn(e,'admission'),false);
 assert.ok(!M.formalComparisons(M.buildBoard(data),'placement-v1.1').some(r=>r.id===id));
 assert.equal(e.execution_chain.q13_RMSE_passed,false);assert.ok(e.execution_chain.q13_RMSE_rad>.005);
 assert.equal(e.topology.original_job_count,1);assert.equal(e.topology.original_GPUs,4);assert.equal(e.topology.original_job_id,'job-txdf93hin5hn');
 assert.equal(e.new_GPU_jobs,0);assert.equal(e.source_raw_reread_in_this_audit,false);assert.equal(e.TTC_P1_condition_triggered,false);
});

test('100 original P1/K pairs reproduce counts, phase, orders and non-improvement bounds',()=>{
 assert.equal(pairs.length,100);assert.equal(new Set(pairs.map(p=>p.order+':'+p.seed)).size,100);
 assert.deepEqual([...pairs.map(p=>p.seed)].sort((a,b)=>a-b),Array.from({length:100},(_,i)=>739000+i));
 const total=k=>pairs.reduce((a,p)=>a+Number(p[k]),0);
 assert.equal(total('P1_success'),4);assert.equal(total('K_success'),5);assert.equal(total('P1_phase'),260);assert.equal(total('K_phase'),238);
 const hist={};for(const p of pairs)hist[p.P1_phase]=(hist[p.P1_phase]||0)+1;assert.deepEqual(hist,e.phase_hist);
 for(const [label,order]of [['left','1234'],['right','4321']]){const p=pairs.filter(p=>p.order===order),r=e.lr_split[label];assert.equal(p.length,50);assert.equal(p.reduce((a,x)=>a+Number(x.P1_success),0),r.success);assert.equal(p.reduce((a,x)=>a+x.P1_phase,0)/50,r.mean_phase);}
 assert.deepEqual(e.paired_P1_minus_K,{phase_difference:.22,phase_CI95:[-.32,.76],SR_difference:-.01,SR_CI95:[-.07,.05]});
 assert.equal(e.paired_baseline_mean_phase,2.38);assert.equal(e.paired_baseline_oracle,'placement-v1.1');
 assert.equal(data.evaluations.find(r=>r.id===e.paired_baseline_evaluation_id).mean_phase,2.38);
 assert.equal(data.evaluations.find(r=>r.id==='task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8').success,7);
 for(const k of ['strict','strict_fdvel']){const r=e.oracle_comparison[k];assert.deepEqual([r.success,r.failure,r.unknown,r.censored],[0,96,4,4]);assert.equal(r.complete_verdict_success_rate,null);assert.equal(Object.hasOwn(r,'phase_hist'),false);}
});

test('P1 and ABC source bytes remain independently pinned with causal and codec limits',()=>{
 for(const r of Object.values(s.sources)){assert.equal(fs.statSync(r.file).size,r.bytes);assert.equal(sha(r.file),r.sha256);}
 assert.equal(sha(root+'FINAL_P1_POLICY100_DIAGNOSTIC.json'),'466e62ac73cb778153e4c0d720e6e9df23a625f7feef7019fef7b725fd2747b8');
 assert.equal(sha(root+'ROOT_P1_PAIR_VERIFICATION.json'),'15867cabd04356d9381e0051c9abb02cc019f13f1922f2ceec3628944cd7cbd9');
 assert.equal(sha(root+'PAIRED100.json'),'d4ea43d198b52bd9af1c63a9cc8e03b7e9a855633932f288323365c71e081328');
 assert.equal(s.boundaries.B_exposure_state_confound_ticks,3);assert.equal(s.boundaries.exact_historical_B_exposure_state,'unknown');
 assert.equal(s.boundaries.offline_C_B_frames,3);assert.equal(s.boundaries.offline_C_lookahead,40);assert.equal(s.boundaries.closedloop_codec_B_frames,0);assert.equal(s.boundaries.same_bitstream,false);
 assert.equal(s.independent_pair_verification.small_closure_full_SHA_verified,100);assert.equal(s.independent_pair_verification.source_raw_reread_in_this_audit,false);
});
