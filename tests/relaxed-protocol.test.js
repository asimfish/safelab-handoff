const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const M=require('../model.js');
const data=JSON.parse(fs.readFileSync('data.json'));

test('relaxed rescores are indexed as diagnostic and cannot replace baseline scores',()=>{
 const baseline={id:'strict-fixture',record:'5-pos-mem0',checkpoint:30000,horizon:8,success:2,trials:100,completed:100,unknown:0,kind:'自主闭环'};
 const candidate={...baseline,id:'relaxed-fixture',success:80,protocol_version:'SafeLab-Eval-v1.2-relaxed',oracle_version:'placement-v1.2-relaxed',stage:'diagnostic',metric_role:'rescored_v1.2_relaxed',formal_score_eligible:false,kind:'放宽判定离线重算 · 诊断'};
 const snapshot=structuredClone(data);snapshot.evaluations=[baseline,candidate];snapshot.diagnostics=[];
 const board=M.buildBoard(snapshot);const indexed=M.evaluationIndex(board);
 assert.equal(indexed.find(e=>e.id===candidate.id).phase,'diagnostic');
 assert.equal(M.resultFor([baseline,candidate],8).success,2);
 assert.equal(M.resultFor([candidate],8),null);
 assert.ok(M.formalIssues(candidate).length);
 assert.equal(M.formalComparisons(board).length,0);
});

test('published relaxed rows preserve unknown and valid-phase denominators',()=>{
 for(const e of data.evaluations.filter(e=>e.protocol_version==='SafeLab-Eval-v1.2-relaxed')){
  assert.equal(e.stage,'diagnostic');assert.equal(e.formal_score_eligible,false);
  assert.equal(e.oracle_version,'placement-v1.2-relaxed');
  assert.equal(Object.values(e.phase_hist).reduce((a,b)=>a+b,0),e.trials-e.unknown);
  assert.equal(e.seed_results.reduce((a,b)=>a+b.trials,0),e.trials);
  assert.equal(e.seed_results.reduce((a,b)=>a+b.unknown,0),e.unknown);
  assert.equal(e.lr_split.left.trials+e.lr_split.right.trials,e.trials);
  assert.equal(e.lr_split.left.unknown+e.lr_split.right.unknown,e.unknown);
  assert.ok(e.report_url.endsWith('task5-relaxed-20261105.html'));
 }
});
