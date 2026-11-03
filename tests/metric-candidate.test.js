'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model'),C=require('../coverage');
const raw=JSON.parse(fs.readFileSync('data.json'));
const fixture=(patch={})=>({id:'candidate-fixture',record:'3-v13-mem0',dataset:'3-v13',checkpoint:30000,horizon:8,protocol_version:M.PROTOCOL,stage:'diagnostic',metric_role:'rescored_v1.1_candidate',source_evaluation_id:'strict-fixture',source:'offline-report.json',completed:100,trials:100,success:30,unknown:2,phase_hist:{0:68,3:30},mean_phase:90/98,condition_version:'original-v1',...patch});
function board(evaluations){return M.buildBoard({...raw,evaluations});}
test('candidate diagnostic computes full denominator but never strict or legacy score or A/B coverage',()=>{
 const e=fixture(),b=board([e]),rows=M.rescoredCandidates(b);assert.equal(rows.length,1);assert.deepEqual(rows[0].wilson95,M.wilson95(30,100));assert.equal(rows[0].sensitivity_upper,.32);assert.equal(rows[0].valid_trials,98);
 assert.equal(M.formalComparisons(b).length,0);assert.equal(M.resultFor([e],8),null);assert.equal(C.stageCoverage([e],'A')[0].state,'未开始');
 const mislabeled={...e,stage:'A'};assert.ok(M.formalIssues(mislabeled).includes('诊断或辅助指标'));assert.equal(M.formalComparisons(board([mislabeled])).length,0);assert.equal(C.stageCoverage([mislabeled],'A')[0].state,'未开始');
});
test('candidate rejects incomplete, nonconserving or untraceable results; all unknown has no mean',()=>{
 for(const p of [{success:null},{completed:99},{unknown:3},{mean_phase:0},{source_evaluation_id:''},{source:'',report_url:''},{evaluation_started:false}])assert.equal(M.rescoredCandidates(board([fixture(p)])).length,0,JSON.stringify(p));
 assert.equal(M.rescoredCandidates(board([fixture({success:0,unknown:100,phase_hist:{},mean_phase:null})]))[0].valid_trials,0);
});
test('metric selector defaults strict and renders candidate data only after explicit selection',()=>{
 const src=fs.readFileSync('app.js','utf8'),body=src.slice(src.indexOf('function candidateTable(){'),src.indexOf('function coverageTable(){'));
 const render=Function('M','board','esc','taskName','camera','link','view',body+';return formalTable(view);');
 const b=board([fixture()]),args=[M,b,String,String,String,()=>'<a>报告</a>'];
 const strict=render(...args,undefined);assert.match(strict,/value="strict-v1" selected/);assert.doesNotMatch(strict,/data-candidate=/);assert.doesNotMatch(strict,/30\.0%/);
 const candidate=render(...args,'v1.1-candidate');assert.match(candidate,/value="v1.1-candidate" selected/);assert.match(candidate,/data-candidate="candidate-fixture"/);assert.match(candidate,/30\.0%/);assert.match(candidate,/尚未采用为正式标准/);
});
test('four dedicated30k checkpoint issues bind correct records and never reuse issue9',()=>{
 for(const [number,id]of [[38,'3-v13-mem0'],[39,'7-mem0'],[40,'7-ours-trainresize'],[41,'7-aligned']]){
  const r=raw.records.find(r=>r.id===id),b=r.checkpoint_issues.find(i=>i.number===number);assert.ok(b);assert.equal(b.checkpoint,30000);assert.equal(b.delivery_document,r.doc);assert.ok(r.weights.some(w=>w.step===30000&&w.path===b.delivery_path));
  assert.equal(raw.checkpoint_issue_audit.bindings.filter(i=>i.number===number).length,1);
 }
 assert.equal(raw.records.find(r=>r.id==='3-v13-mem0').checkpoint_issues.find(i=>i.number===9).checkpoint,20000);
});
