'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model');
const data=JSON.parse(fs.readFileSync('data.json'));
function valid(overrides={}){return {id:'v1-fixture',record:'3-v13-mem0',dataset:'3-v13',method:'Mem-0',checkpoint:30000,horizon:8,protocol_version:M.PROTOCOL,stage:'A',success:3,trials:100,unknown:2,completed:100,kind:'自主闭环',protocol:'fixture',topology:{num_envs_actual:1,procs_per_gpu:2,gpu_type:'Pro6000'},preprocess_resize:{implementation:'training_tensor',mode:'bilinear',antialias:true,source:'train.py@sha'},condition_version:'original-v1',scene_list_hash:'sha256:'+'a'.repeat(64),lr_split:{left:{trials:50,success:1,unknown:1},right:{trials:50,success:2,unknown:1}},seed_results:[{seed:0,trials:100,success:3,unknown:2}],mean_phase:9/98,phase_hist:{0:95,3:3},admission:Object.fromEntries(['expert_replay','open_loop','render_multiframe','smoke20'].map(k=>[k,{passed:true,report:'fixture-only'}])),...overrides};}
test('migration preserves all167 legacy records and their original protocol',()=>{assert.ok(data.evaluations.length>=167);for(const e of data.evaluations.filter(e=>e.protocol_version==='legacy')){assert.equal(e.stage,'legacy');assert.equal(e.protocol,e.legacy_protocol);for(const k of ['topology','preprocess_resize','condition_version','scene_list_hash','lr_split','mean_phase','phase_hist','wilson95'])assert.ok(Object.hasOwn(e,k));}const d=structuredClone(data);d.evaluations=d.evaluations.filter(e=>e.protocol_version==='legacy');assert.equal(M.formalComparisons(M.buildBoard(d)).length,0);});
test('valid A enters formal table; unknown remains in denominator and Wilson computed',()=>{const e=valid();assert.deepEqual(M.formalIssues(e),[]);const d=structuredClone(data);d.evaluations=[e];const rows=M.formalComparisons(M.buildBoard(d));assert.equal(rows.length,1);assert.equal(rows[0].trials,100);assert.equal(rows[0].unknown,2);assert.ok(rows[0].wilson95.low<.03&&rows[0].wilson95.high>.03);});
test('legacy, diagnostic, vectorized, incomplete, wrong resize or missing admission never enter',()=>{for(const patch of [{protocol_version:'legacy'},{stage:'diagnostic'},{topology:{num_envs_actual:4,procs_per_gpu:1,gpu_type:'Pro6000'}},{success:null,completed:20},{horizon:30},{preprocess_resize:{implementation:'PIL',mode:'bicubic'}},{admission:{}},{mean_phase:1},{scene_list_hash:'missing'},{lr_split:null},{seed_results:[]}])assert.ok(M.formalIssues(valid(patch)).length,JSON.stringify(patch));});
test('best configuration selected only within same protocol cohort; attach versions never pooled',()=>{const d=structuredClone(data);d.evaluations=[valid({id:'h4',horizon:4}),valid({id:'h8'}),valid({id:'attach1',condition_version:'attach-v1'}),valid({id:'attach2',condition_version:'attach-v2_solver128'})];const rows=M.formalComparisons(M.buildBoard(d));assert.equal(rows.length,3);assert.deepEqual(new Set(rows.map(x=>x.condition_version)),new Set(['original-v1','attach-v1','attach-v2_solver128']));});
test('B requires five complete100-trial seeds and balanced250/250 split',()=>{const e=valid({stage:'B',trials:500,completed:500,success:15,unknown:10,lr_split:{left:{trials:250,success:5,unknown:5},right:{trials:250,success:10,unknown:5}},seed_results:Array.from({length:5},(_,seed)=>({seed,trials:100,success:3,unknown:2})),phase_hist:{0:475,3:15}});assert.deepEqual(M.formalIssues(e),[]);e.seed_results[4].seed=0;assert.ok(M.formalIssues(e).length);});

test('all archived evaluation rows declare protocol schema; v1 complete records require evidence',()=>{for(const e of data.evaluations){for(const k of ['protocol_version','stage','topology','preprocess_resize','condition_version','scene_list_hash','lr_split','mean_phase','phase_hist','wilson95'])assert.ok(Object.hasOwn(e,k),e.id+': '+k);assert.ok(['A','B','diagnostic','legacy'].includes(e.stage));if([M.PROTOCOL,M.CURRENT_PROTOCOL].includes(e.protocol_version)&&['A','B'].includes(e.stage)&&e.success!==null)assert.deepEqual(M.formalIssues(e),[],e.id);}});

test('A unknown phases exclude unknown while full denominator and sensitivity bound remain100',()=>{
 const e=valid({failure:95,unknown_reasons:{infrastructure:1,unjudged:1}});
 assert.deepEqual(M.formalIssues(e),[]);
 const d=structuredClone(data);d.evaluations=[e];const row=M.formalComparisons(M.buildBoard(d))[0];
 assert.ok(row);assert.equal(row.valid_trials,98);assert.equal(row.trials,100);assert.equal(row.sensitivity_upper,.05);
 assert.deepEqual(row.wilson95,M.wilson95(3,100));assert.notDeepEqual(row.wilson95,M.wilson95(3,98));
});
test('unknown=0 retains original phase statistics and sensitivity equals success rate',()=>{
 const e=valid({unknown:0,lr_split:{left:{trials:50,success:1,unknown:0},right:{trials:50,success:2,unknown:0}},seed_results:[{seed:0,trials:100,success:3,unknown:0}],phase_hist:{0:97,3:3},mean_phase:.09});
 assert.deepEqual(M.formalIssues(e),[]);const d=structuredClone(data);d.evaluations=[e];const row=M.formalComparisons(M.buildBoard(d))[0];assert.equal(row.valid_trials,100);assert.equal(row.sensitivity_upper,.03);
});
test('phase total and mean must conserve valid trials, never include unknown as zero-phase',()=>{
 for(const patch of [{phase_hist:{0:97,3:3}},{phase_hist:{0:94,3:3}},{mean_phase:.09}])assert.ok(M.formalIssues(valid(patch)).includes('阶段统计不完整'));
});
test('explicit failure and unknown reason counts must conserve outcomes',()=>{
 for(const patch of [{failure:94},{unknown_reasons:{infrastructure:3}},{lr_split:{left:{trials:50,success:1,failure:49,unknown:1},right:{trials:50,success:2,unknown:1}}},{seed_results:[{seed:0,trials:100,success:3,failure:97,unknown:2}]}])assert.ok(M.formalIssues(valid(patch)).length,JSON.stringify(patch));
});
test('all unknown has no measured mean and no fabricated failure phase',()=>{
 const e=valid({success:0,unknown:100,lr_split:{left:{trials:50,success:0,unknown:50},right:{trials:50,success:0,unknown:50}},seed_results:[{seed:0,trials:100,success:0,unknown:100}],mean_phase:null,phase_hist:{}});
 assert.deepEqual(M.formalIssues(e),[]);const d=structuredClone(data);d.evaluations=[e];const row=M.formalComparisons(M.buildBoard(d))[0];assert.equal(row.valid_trials,0);assert.equal(row.sensitivity_upper,1);assert.ok(M.formalIssues({...e,mean_phase:0}).length);
});

test('actual formal table template shows full-denominator score, unknown bound and valid phase count',()=>{
 const source=fs.readFileSync('app.js','utf8'),start=source.indexOf('function oracleTable('),end=source.indexOf('function render(){',start);
 const render=Function('M','board','esc','taskName','camera',source.slice(start,end)+';return formalTable();');
 const d=structuredClone(data);d.evaluations=[valid()];
 const html=render(M,M.buildBoard(d),String,String,String);
 assert.match(html,/3\.0%/);assert.match(html,/unknown 2/);assert.match(html,/unknown 全部成功上界 5\.0%/);assert.match(html,/有效 98\/100/);
 const e=valid({success:0,unknown:100,lr_split:{left:{trials:50,success:0,unknown:50},right:{trials:50,success:0,unknown:50}},seed_results:[{seed:0,trials:100,success:0,unknown:100}],mean_phase:null,phase_hist:{}});
 d.evaluations=[e];const empty=render(M,M.buildBoard(d),String,String,String);assert.match(empty,/无有效轨迹/);assert.match(empty,/unknown 全部成功上界 100\.0%/);
});
