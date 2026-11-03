(function(root){
'use strict';
const M=typeof module!=='undefined'?require('./model'):root.HandoffModel;
const latest=rows=>rows.reduce((best,e)=>{const t=Date.parse(e.updated_at||e.issue_updated_at||'');return Number.isFinite(t)&&t>best?t:best;},0);
function conditionState(rows,stage){
 const completed=rows.filter(e=>M.formalIssues(e).length===0);
 if(completed.length===rows.length)return {state:'完成',rows};
 const ready=rows.filter(e=>['expert_replay','open_loop','render_multiframe','smoke20'].every(k=>e.admission?.[k]?.passed===true)&&e.valid_for_comparison!==false);
 if(ready.some(e=>e.completed>0))return {state:'阶段 '+stage+' 进行中',rows};
 const smoke=rows.some(e=>['expert_replay','open_loop','render_multiframe'].every(k=>e.admission?.[k]?.passed===true)&&e.admission?.smoke20?.passed!==true);
 return {state:smoke?'冒烟':'准入中',rows};
}
function stageCoverage(evaluations,stage){
 const rows=evaluations.filter(e=>e.protocol_version===M.PROTOCOL&&e.stage===stage&&e.metric_role!=='rescored_v1.1_candidate'),groups=new Map();
 for(const e of rows){const key=e.condition_version||'条件版本待补';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}
 return rows.length?[...groups].map(([condition,rows])=>{
  const horizons=[4,8].map(horizon=>{const cohort=rows.filter(e=>e.horizon===horizon);return {horizon,...(cohort.length?conditionState(cohort,stage):{state:'未开始',rows:[]})};});
  const states=horizons.map(h=>h.state),state=states.every(s=>s==='完成')?'完成':states.some(s=>s==='完成'||s.includes('进行中'))?'阶段 '+stage+' 进行中':states.includes('冒烟')?'冒烟':states.includes('准入中')?'准入中':'未开始';
  return {condition,state,rows,horizons};
 }):[{condition:null,state:'未开始',rows:[],horizons:[]}];
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
  const hasV1=evaluations.some(e=>e.protocol_version===M.PROTOCOL),hasAB=evaluations.some(e=>e.protocol_version===M.PROTOCOL&&['A','B'].includes(e.stage)&&e.metric_role!=='rescored_v1.1_candidate');
  const liveOwner=members.filter(r=>r.shared&&r.owner!=='未指定'&&!/训练/.test(r.owner)).sort((a,b)=>Date.parse(b.shared.updated)-Date.parse(a.shared.updated))[0]?.owner;
  const owner=liveOwner||issues.find(i=>i.evaluation_owner)?.evaluation_owner||evaluations.find(e=>e.owner||e.agent)?.owner||evaluations.find(e=>e.agent)?.agent||members.find(r=>r.owner!=='未指定'&&!/训练/.test(r.owner))?.owner||'待分配';
  const time=Math.max(latest(evaluations),latest(issues),latest(members.map(r=>({updated_at:r.record?.updated_at}))),latest(members.filter(r=>r.shared).map(r=>({updated_at:r.shared.updated}))));
  return {id,rowKey:representative.key,task:representative.task,dataset:representative.dataset,camera:representative.camera,method:representative.method,step:representative.step,path:representative.path,doc:representative.doc,issues,evaluations,memberKeys:members.map(r=>r.key),missingV1:!hasV1,hasAB,stageA:stageCoverage(evaluations,'A'),stageB:stageCoverage(evaluations,'B'),owner,updated:time?new Date(time).toISOString():null};
 }).sort((a,b)=>Number(a.task)-Number(b.task)||a.dataset.localeCompare(b.dataset)||a.method.localeCompare(b.method)||a.step-b.step);
}
const api={checkpointCoverage,stageCoverage};if(typeof module!=='undefined')module.exports=api;root.HandoffCoverage=api;
})(typeof window==='undefined'?globalThis:window);
