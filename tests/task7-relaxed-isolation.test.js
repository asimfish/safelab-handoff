'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model'),C=require('../coverage');
const data=JSON.parse(fs.readFileSync('data.json')),original=data.evaluations.find(e=>e.id==='task7-eval-v11-A-original-mem0_30k-h8');
function fixture(){return {...structuredClone(original),id:'test-only-relaxed-source-fixture',protocol_version:'SafeLab-Eval-v1.2-relaxed',oracle_version:'placement-v1.2-relaxed',stage:'diagnostic',metric_role:'offline_rescore_v1_2_relaxed',kind:'CPU离线重算诊断',formal_score_eligible:false,source_evaluation_id:original.id,qualification:{passed:false,status:'pending'}};}
test('new relaxed diagnostic protocol is retained without changing the current formal protocol',()=>{
 const f=fixture(),board=M.buildBoard({...data,evaluations:[...data.evaluations,f]});
 assert.equal(M.CURRENT_PROTOCOL,'SafeLab-Eval-v1.1');assert.equal(M.isRevoked(f),false);
 assert.ok(M.evaluationIndex(board).some(e=>e.id===f.id));assert.ok(M.formalIssues(f).length);
 assert.equal(M.formalComparisons(board).some(e=>e.id===f.id),false);assert.equal(M.resultFor([f],8),null);
});
test('a relaxed source link does not merge into original oracle results or stageA coverage',()=>{
 const before=M.buildBoard(data),after=M.buildBoard({...data,evaluations:[...data.evaluations,fixture()]});
 assert.deepEqual(M.oracleComparisons(after),M.oracleComparisons(before));
 const coverage=b=>C.checkpointCoverage(b).map(r=>({rowKey:r.rowKey,missingV1:r.missingV1,hasAB:r.hasAB,stageA:r.stageA,stageB:r.stageB,variants:r.variants.map(v=>({stageA:v.stageA,stageB:v.stageB}))}));
 assert.deepEqual(coverage(after),coverage(before));
 assert.deepEqual(data.evaluations.find(e=>e.id===original.id),original);
});
test('schema keeps relaxed qualification and source-prefix semantics explicit',()=>{
 const doc=fs.readFileSync('docs/evaluation-schema-v1.md','utf8');
 for(const text of ['SafeLab-Eval-v1.2-relaxed','placement-v1.2-relaxed','offline_rescore_v1_2_relaxed','qualification.passed:false','SR@7','observed_phase_lower_bound','phase_known_n','完全缺 raw','CURRENT_PROTOCOL'])assert.ok(doc.includes(text),text);
 assert.equal(fixture().qualification.passed,false);
});
