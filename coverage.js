(function(root){
'use strict';
const M=typeof module!=='undefined'?require('./model'):root.HandoffModel;
const latest=rows=>rows.reduce((best,e)=>{const t=Date.parse(e.updated_at||e.issue_updated_at||'');return Number.isFinite(t)&&t>best?t:best;},0);
function conditionState(rows,stage){
 const metadata=()=>({reason:rows.find(e=>e.pending_reason||e.blocker||e.note)?.pending_reason||rows.find(e=>e.blocker)?.blocker||'尚未登记 v1.1 执行进度',expected_start_at:rows.find(e=>e.expected_start_at)?.expected_start_at||null});
 if(rows.every(e=>M.formalIssues(e).length===0))return {state:'完成',rows,...metadata()};
 const ready=e=>M.admissionKeys(e).every(k=>e.admission?.[k]?.passed===true&&e.admission[k].report);
 if(rows.some(e=>ready(e)&&e.completed>0))return {state:'阶段 '+stage+' 进行中',rows,...metadata()};
 const smoke=rows.some(e=>['expert_replay','open_loop','render_multiframe','executor_parity'].every(k=>e.admission?.[k]?.passed===true)&&e.admission?.smoke20?.passed!==true);
 const admissionWork=rows.some(e=>Object.values(e.admission||{}).some(g=>g.passed===true||g.status==='running')||e.status==='admission_in_progress');
 return {state:smoke?'冒烟':admissionWork&&!rows.every(ready)?'准入中':'未开始',rows,...metadata()};
}
function stageCoverage(evaluations,stage,plannedConditions=[]){
 const rows=evaluations.filter(e=>e.protocol_version===M.CURRENT_PROTOCOL&&e.oracle_version==='placement-v1.1'&&e.stage===stage&&!M.isRevoked(e)),groups=new Map();
 for(const condition of plannedConditions)groups.set(condition,[]);
 for(const e of rows){const key=e.condition_version||'条件版本待补';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}
 if(!groups.size)groups.set('original-v1',[]);
 return [...groups].map(([condition,rows])=>{
  const horizons=[4,8].map(horizon=>{const cohort=rows.filter(e=>e.horizon===horizon);return {horizon,...(cohort.length?conditionState(cohort,stage):{state:'未开始',rows:[],reason:'尚无 v1.1 '+stage+' 阶段登记；等待负责人提供准入与排期',expected_start_at:null})};});
  const states=horizons.map(h=>h.state),state=states.every(s=>s==='完成')?'完成':states.some(s=>s==='完成'||s.includes('进行中'))?'阶段 '+stage+' 进行中':states.includes('冒烟')?'冒烟':states.includes('准入中')?'准入中':'未开始';
  return {condition,state,rows,horizons};
 });
}
function checkpointCoverage(board){
 const groups=new Map();
 for(const row of board.rows){
  if(row.step<1||!(row.path||row.doc||row.issue_bindings?.length))continue;
  // Different evaluation conditions using the identical physical checkpoint share one row.
  const identity=JSON.stringify([row.task,row.dataset,row.camera,row.step,row.path||('document:'+row.doc+'|'+row.method)]);
  if(!groups.has(identity))groups.set(identity,[]);groups.get(identity).push(row);
 }
 return [...groups].map(([id,members])=>{
  const representative=members.find(r=>r.issue_bindings?.some(i=>!i.duplicate_of))||members[0],evaluations=[...new Map(members.flatMap(r=>r.evaluations).map(e=>[e.id,e])).values()];
  const issues=[...new Map(members.flatMap(r=>r.issue_bindings||[]).map(i=>[i.number,i])).values()].sort((a,b)=>a.number-b.number);
  const hasV1=evaluations.some(e=>e.protocol_version===M.CURRENT_PROTOCOL&&e.oracle_version==='placement-v1.1'),hasAB=evaluations.some(e=>e.protocol_version===M.CURRENT_PROTOCOL&&e.oracle_version==='placement-v1.1'&&['A','B'].includes(e.stage));
  const variants=members.map(row=>{const ev=row.evaluations.filter(e=>!M.isRevoked(e)),conditions=[...new Set(ev.map(e=>e.condition_version).filter(v=>v&&!/^diagnostic-/i.test(v)))];if(!/附着|attach/i.test(row.method)&&!conditions.includes('original-v1'))conditions.unshift('original-v1');if(!conditions.length)conditions.push('附着版本待登记');return {rowKey:row.key,method:row.method,stageA:stageCoverage(ev,'A',conditions),stageB:stageCoverage(ev,'B',conditions)};});
  const liveOwner=members.filter(r=>r.shared&&r.owner!=='未指定'&&!/训练/.test(r.owner)).sort((a,b)=>Date.parse(b.shared.updated)-Date.parse(a.shared.updated))[0]?.owner;
  const owner=liveOwner||issues.find(i=>i.evaluation_owner)?.evaluation_owner||evaluations.find(e=>e.owner||e.agent)?.owner||evaluations.find(e=>e.agent)?.agent||members.find(r=>r.owner!=='未指定'&&!/训练/.test(r.owner))?.owner||'待分配';
  const time=Math.max(latest(evaluations),latest(issues),latest(members.map(r=>({updated_at:r.record?.updated_at}))),latest(members.filter(r=>r.shared).map(r=>({updated_at:r.shared.updated}))));
  return {id,rowKey:representative.key,task:representative.task,dataset:representative.dataset,camera:representative.camera,method:representative.method,step:representative.step,path:representative.path,doc:representative.doc,issues,evaluations,memberKeys:members.map(r=>r.key),missingV1:!hasV1,hasAB,variants,stageA:variants.flatMap(v=>v.stageA.map(c=>({...c,variant:v.method,variantKey:v.rowKey}))),stageB:variants.flatMap(v=>v.stageB.map(c=>({...c,variant:v.method,variantKey:v.rowKey}))),owner,updated:time?new Date(time).toISOString():null};
 }).sort((a,b)=>Number(a.task)-Number(b.task)||a.dataset.localeCompare(b.dataset)||a.method.localeCompare(b.method)||a.step-b.step);
}
const api={checkpointCoverage,stageCoverage};if(typeof module!=='undefined')module.exports=api;root.HandoffCoverage=api;
})(typeof window==='undefined'?globalThis:window);
