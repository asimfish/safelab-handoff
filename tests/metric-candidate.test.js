'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model'),C=require('../coverage');
const raw=JSON.parse(fs.readFileSync('data.json'));
const fixture=(patch={})=>({id:'candidate-fixture',record:'3-v13-mem0',dataset:'3-v13',checkpoint:30000,horizon:8,protocol_version:M.PROTOCOL,stage:'diagnostic',metric_role:'rescored_v1.1_candidate',source_evaluation_id:'strict-fixture',source:'offline-report.json',completed:100,trials:100,success:30,unknown:2,phase_hist:{0:68,3:30},mean_phase:90/98,condition_version:'original-v1',...patch});
function board(evaluations){return M.buildBoard({...raw,evaluations,diagnostics:[]});}
test('revoked drift candidates disappear from every board table and coverage',()=>{
 const e=fixture(),b=board([e]);assert.equal(M.rescoredCandidates(b).length,0);assert.equal(M.evaluationIndex(b).length,0);assert.ok(b.rows.every(r=>r.evaluations.length===0));assert.equal(M.formalComparisons(b).length,0);assert.equal(M.resultFor([e],8),null);assert.equal(C.stageCoverage([e],'A')[0].state,'未开始');
 const d={...raw,evaluations:[],diagnostics:[e]};assert.equal(M.buildBoard(d).diagnostics.length,0);
});
test('four dedicated30k checkpoint issues bind correct records and never reuse issue9',()=>{
 for(const [number,id]of [[38,'3-v13-mem0'],[39,'7-mem0'],[40,'7-ours-trainresize'],[41,'7-aligned']]){
  const r=raw.records.find(r=>r.id===id),b=r.checkpoint_issues.find(i=>i.number===number);assert.ok(b);assert.equal(b.checkpoint,30000);assert.equal(b.delivery_document,r.doc);assert.ok(r.weights.some(w=>w.step===30000&&w.path===b.delivery_path));
  assert.equal(raw.checkpoint_issue_audit.bindings.filter(i=>i.number===number).length,1);
 }
 assert.equal(raw.records.find(r=>r.id==='3-v13-mem0').checkpoint_issues.find(i=>i.number===9).checkpoint,20000);
});
