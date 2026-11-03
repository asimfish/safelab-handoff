'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model'),C=require('../coverage'),raw=require('../data.json');
const admission=()=>Object.fromEntries(['expert_replay','open_loop','render_multiframe','smoke20','executor_parity'].map(k=>[k,{passed:true,report:'fixture-only'}]));
function valid(patch={}){return {id:'placement-fixture',record:'3-v13-mem0',dataset:'3-v13',checkpoint:30000,horizon:8,protocol_version:M.CURRENT_PROTOCOL,oracle_version:'placement-v1.1',stage:'A',completed:100,trials:100,success:3,unknown:2,kind:'自主闭环',condition_version:'original-v1',scene_list_hash:'sha256:'+'a'.repeat(64),topology:{num_envs_actual:1,procs_per_gpu:2,gpu_type:'Pro6000'},preprocess_resize:{implementation:'training_tensor',mode:'bilinear',antialias:true,source:'fixture'},lr_split:{left:{trials:50,success:1,unknown:1},right:{trials:50,success:2,unknown:1}},seed_results:[{seed:0,trials:100,success:3,unknown:2}],phase_hist:{0:95,3:3},mean_phase:9/98,admission:admission(),...patch};}
function board(evaluations,records=raw.records){return M.buildBoard({...raw,records,evaluations,diagnostics:[]});}
test('v1.1 accepts conserved unknown statistics only with placement oracle and executor parity',()=>{
 const e=valid();assert.deepEqual(M.formalIssues(e),[]);const row=M.formalComparisons(board([e]))[0];assert.equal(row.trials,100);assert.equal(row.valid_trials,98);assert.equal(row.sensitivity_upper,.05);assert.deepEqual(row.wilson95,M.wilson95(3,100));
 for(const patch of [{oracle_version:null},{oracle_version:'strict-v1'},{phase_hist:{0:97,3:3}},{mean_phase:.09},{lr_split:null},{seed_results:[]},{unknown_reasons:{missing_log:3}},{admission:{...admission(),executor_parity:{passed:true,report:''}}},{admission:{...admission(),executor_parity:{passed:false,report:'not passed'}}}])assert.ok(M.formalIssues(valid(patch)).length,JSON.stringify(patch));
 const gates=admission();delete gates.executor_parity;assert.ok(M.formalIssues(valid({admission:gates})).includes('准入证据缺失'));
});
test('v1.1 B preserves five seeds and all-unknown denominator',()=>{
 const e=valid({stage:'B',completed:500,trials:500,success:0,unknown:500,phase_hist:{},mean_phase:null,lr_split:{left:{trials:250,success:0,unknown:250},right:{trials:250,success:0,unknown:250}},seed_results:Array.from({length:5},(_,seed)=>({seed,trials:100,success:0,unknown:100}))});assert.deepEqual(M.formalIssues(e),[]);assert.equal(M.formalComparisons(board([e]))[0].sensitivity_upper,1);e.seed_results[4].seed=0;assert.ok(M.formalIssues(e).length);
});
test('automatic oracle choice is per task; invalid v1.1 never hides strict and protocols never pool',()=>{
 const strict=valid({id:'strict',protocol_version:M.PROTOCOL,oracle_version:'strict-v1'}),placement=valid(),seven=valid({id:'seven-strict',record:'7-mem0',dataset:'7-weigh',protocol_version:M.PROTOCOL,oracle_version:'strict-v1'});
 let b=board([strict,placement,seven]);let rows=M.formalComparisons(b);assert.equal(rows.length,2);assert.equal(rows.find(e=>e.task==='3').oracle_version,'placement-v1.1');assert.equal(rows.find(e=>e.task==='7').oracle_version,'strict-v1');assert.equal(M.formalComparisons(b,'strict-v1').length,2);assert.equal(M.formalComparisons(b,'placement-v1.1').length,1);
 b=board([strict,{...placement,admission:{}},seven]);assert.equal(M.formalComparisons(b).find(e=>e.task==='3').id,'strict');
 assert.ok(M.formalIssues({...strict,oracle_version:'placement-v1.1'}).length);assert.deepEqual(M.formalIssues({...strict,oracle_version:undefined}),[]);
});
test('strict scores and revoked drift candidates never count toward v1.1 coverage',()=>{
 const strict=valid({protocol_version:M.PROTOCOL,oracle_version:'strict-v1'}),candidate=valid({metric_role:'rescored_v1.1_candidate',stage:'diagnostic'});const b=board([strict,candidate]);assert.equal(M.evaluationIndex(b).some(e=>M.isRevoked(e)),false);const row=C.checkpointCoverage(b).find(r=>r.rowKey==='3-v13-mem0@30000');assert.ok(row.missingV1);assert.ok(row.stageA.every(c=>c.horizons.every(h=>h.state==='未开始')));
});
test('coverage exposes same-file variants and every H4/H8 condition with missing reason and schedule',()=>{
 const base=raw.records.find(r=>r.id==='3-v13-mem0'),records=[{...base,weights:base.weights.filter(w=>w.step===30000)},{...base,id:'resize-variant',method:'Mem-0 training resize',weights:base.weights.filter(w=>w.step===30000),checkpoint_issues:[]}];
 const e=valid(),h4={...e,id:'h4',horizon:4},attached={...e,id:'attach',condition_version:'attach-test-v1',record:'resize-variant',success:null,completed:0,evaluation_started:false,admission:{},pending_reason:'等待执行链',expected_start_at:'2026-11-04T01:00:00Z'};
 const rows=C.checkpointCoverage(board([e,h4,attached],records));assert.equal(rows.length,1);assert.equal(rows[0].variants.length,2);assert.equal(rows[0].variants[0].stageA[0].state,'完成');const condition=rows[0].variants[1].stageA.find(c=>c.condition==='attach-test-v1');assert.equal(condition.horizons.length,2);assert.equal(condition.horizons.find(h=>h.horizon===8).reason,'等待执行链');assert.equal(condition.horizons.find(h=>h.horizon===8).expected_start_at,attached.expected_start_at);assert.equal(condition.horizons.find(h=>h.horizon===4).state,'未开始');assert.equal(condition.horizons.find(h=>h.horizon===4).expected_start_at,null);
});
test('new standard and homepage link placement oracle and complete execution-chain requirements',()=>{
 const html=fs.readFileSync('eval-v1.1.html','utf8');for(const term of ['一、成功判定','二、执行链','0.25','30 tick','不设任何速度或角速度阈值','episode 结束时','各抽 10 条','0.005 rad','端点链 ≥ 原生链 −1','current_row','pi0.5 预测 10 步'])assert.ok(html.includes(term),term);assert.match(fs.readFileSync('index.html','utf8'),/href="eval-v1\.1\.html"/);assert.match(fs.readFileSync('eval-v1.html','utf8'),/成功判定已由 v1.1 取代/);
});
test('legacy publication repair never fills or promotes either formal protocol',()=>{
 const os=require('node:os'),path=require('node:path'),{spawnSync}=require('node:child_process'),root=fs.mkdtempSync(path.join(os.tmpdir(),'safelab-v11-normalizer-'));
 try{fs.mkdirSync(path.join(root,'scripts'));fs.copyFileSync('scripts/fill-legacy-schema.py',path.join(root,'scripts/fill-legacy-schema.py'));const source={evaluations:[{id:'new-incomplete',protocol_version:M.CURRENT_PROTOCOL,success:null},{id:'strict-incomplete',protocol_version:M.PROTOCOL,success:null},{id:'old',success:2,trials:100,protocol:'old-only'}]};fs.writeFileSync(path.join(root,'data.json'),JSON.stringify(source));const r=spawnSync('python3',[path.join(root,'scripts/fill-legacy-schema.py')],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);const out=JSON.parse(fs.readFileSync(path.join(root,'data.json')));assert.deepEqual(out.evaluations[0],source.evaluations[0]);assert.deepEqual(out.evaluations[1],source.evaluations[1]);assert.equal(out.evaluations[2].stage,'legacy');assert.equal(out.evaluations[2].success,2);}
 finally{fs.rmSync(root,{recursive:true,force:true});}
});
