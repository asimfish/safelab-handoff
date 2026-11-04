'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model'),C=require('../coverage'),raw=require('../data.json');
const admission=()=>Object.fromEntries(['expert_replay','open_loop','render_multiframe','smoke20','executor_parity'].map(k=>[k,{passed:true,report:'fixture-only'}]));
function valid(patch={}){return {id:'placement-fixture',record:'3-v13-mem0',dataset:'3-v13',checkpoint:30000,horizon:8,protocol_version:M.CURRENT_PROTOCOL,oracle_version:'placement-v1.1',stage:'A',completed:100,trials:100,success:3,unknown:2,kind:'自主闭环',condition_version:'original-v1',scene_list_hash:'sha256:'+'a'.repeat(64),topology:{num_envs_actual:1,procs_per_gpu:2,gpu_type:'Pro6000'},preprocess_resize:{implementation:'training_tensor',mode:'bilinear',antialias:true,source:'fixture'},lr_split:{left:{trials:50,success:1,unknown:1},right:{trials:50,success:2,unknown:1}},seed_results:[{seed:0,trials:100,success:3,unknown:2}],phase_hist:{0:95,3:3},mean_phase:9/98,admission:admission(),...patch};}
function board(evaluations,records=raw.records){return M.buildBoard({...raw,records,evaluations,diagnostics:[]});}

test('FD keeps strict protocol, conservation and mandatory same-rollout reference',()=>{
 const fd=valid({id:'fd',protocol_version:M.PROTOCOL,oracle_version:'strict-fdvel-v1',paired_evaluation_id:'strict'});
 assert.deepEqual(M.formalIssues(fd),[]);
 assert.ok(M.formalIssues({...fd,paired_evaluation_id:null}).length);
 assert.ok(M.formalIssues({...fd,protocol_version:M.CURRENT_PROTOCOL}).length);
 assert.ok(M.formalIssues({...fd,phase_hist:{0:97,3:3}}).length);
});
test('three-oracle columns use explicit same-configuration links and never replace formal placement',()=>{
 const strict=valid({id:'strict',protocol_version:M.PROTOCOL,oracle_version:'strict-v1'}),fd={...strict,id:'fd',oracle_version:'strict-fdvel-v1',paired_evaluation_id:'strict'},placement=valid({paired_evaluation_id:'strict'});
 const b=board([strict,fd,placement]),rows=M.oracleComparisons(b);assert.equal(rows.length,1);assert.equal(rows[0].oracles['strict-fdvel-v1'].id,'fd');assert.equal(rows[0].oracles['placement-v1.1'].id,placement.id);assert.equal(M.formalComparisons(b)[0].id,placement.id);
 for(const patch of [{paired_evaluation_id:'absent'},{horizon:4},{condition_version:'attach-v1'},{topology:{num_envs_actual:1,procs_per_gpu:8,gpu_type:'Pro6000'}}]){const r=M.oracleComparisons(board([strict,{...fd,...patch},placement]));assert.ok(r.every(x=>x.oracles['strict-fdvel-v1']?.score_eligible!==true));assert.equal(M.formalComparisons(board([strict,{...fd,...patch},placement]),'strict-fdvel-v1').length,0);}
 const unlinked=M.oracleComparisons(board([strict,valid()]));assert.equal(unlinked.length,2);assert.ok(unlinked.some(x=>!x.oracles['strict-v1']));
});
test('FD incomplete and unknown stay distinct from zero; diagnostic never enters three-way table',()=>{
 const strict=valid({id:'strict',protocol_version:M.PROTOCOL,oracle_version:'strict-v1'}),fd={...strict,id:'fd',oracle_version:'strict-fdvel-v1',paired_evaluation_id:'strict',completed:20,success:null};
 const rows=M.oracleComparisons(board([strict,fd]));assert.equal(rows.length,1);assert.equal(rows[0].oracles['strict-fdvel-v1'].success,null);assert.equal(rows[0].oracles['strict-fdvel-v1'].score_eligible,false);
 assert.equal(M.oracleComparisons(board([{...strict,stage:'diagnostic'}])).length,0);
});

test('actual three-way HTML labels FD comparison and never prints partial success',()=>{
 const source=fs.readFileSync('app.js','utf8'),start=source.indexOf('function oracleTable('),end=source.indexOf('function formalTable(',start),render=Function('M','board','esc','taskName','camera',source.slice(start,end)+';return oracleTable();');
 const strict=valid({id:'strict',protocol_version:M.PROTOCOL,oracle_version:'strict-v1'}),fd={...strict,id:'fd',oracle_version:'strict-fdvel-v1',paired_evaluation_id:'strict',completed:20,success:null};
 const html=render(M,board([strict,fd]),String,String,String);assert.match(html,/FD（对照口径）/);assert.match(html,/未发布/);assert.match(html,/20\/100/);assert.doesNotMatch(html,/NaN|Infinity/);
});
