(function(root){
'use strict';
const STATES={untested:'待评测',evaluating:'评测中',results:'已有结果',training:'训练中',blocked:'阻塞',verify:'待核验'};
const CAMERAS={third_person:'第三人称',chest:'胸部相机',unknown:'相机待确认'};
const TASKS=[{id:'3',name:'三子任务',sub:'抓取 → 倾倒 → 归位',versions:['3-pos3cm-200','3-latest','3-v13','3-jitter']},{id:'5',name:'五子任务',sub:'遮挡任务',versions:['5-pos','5-fixed']},{id:'7',name:'七子任务',sub:'四烧杯称重',versions:['7-weigh']},{id:'10',name:'十子任务',sub:'五烧杯称重',versions:['10-weigh']}];
const VERSIONS={'3-pos3cm-200':'±3cm · 200条','3-latest':'latest / V14','3-v13':'V13 smooth','3-jitter':'早期 jitter1cm','5-pos':'1025 · pos1cm','5-fixed':'1023 · fixed','7-weigh':'v180 · 四杯','10-weigh':'v180 · 五杯'};
const key=(record,step)=>record+'@'+step;
const safeText=(x,max=1500)=>typeof x==='string'&&x.length<=max&&!/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(x);
function parseScore(s){if(!s)return null;const m=/^(\d{1,7})\/(\d{1,7})$/.exec(s.trim());if(!m||+m[2]<1||+m[1]>+m[2])throw Error('成绩须为 成功数/总次数，例如 21/100');return {success:+m[1],trials:+m[2]};}
function validateEdit(x){
 if(!x||x.schema!==2||x.kind!=='checkpoint')throw Error('非交接记录');
 for(const k of ['target','task','dataset','version','data_path','camera','method','path','doc','owner','run','protocol','note','h4','h8'])if(!safeText(x[k],k==='note'?1000:1200))throw Error('字段无效：'+k);
 if(!/^(3|5|7|10|other)$/.test(x.task)||!(/^[a-z0-9][a-z0-9-]{0,79}$/).test(x.dataset))throw Error('任务或数据版本标识无效');
 if(!/^[a-zA-Z0-9@:_-]{0,160}$/.test(x.target)||!Object.hasOwn(CAMERAS,x.camera)||!Object.hasOwn(STATES,x.state))throw Error('状态、相机或关联标识无效');
 if(!Number.isInteger(x.step)||x.step<0||x.step>1000000000||!x.version.trim()||!x.method.trim())throw Error('版本、方法或步数未填写');
 if(!['training','verify','blocked'].includes(x.state)&&(!x.path.trim()||x.step<1))throw Error('已交付权重需要路径和训练步数');
 for(const h of ['h4','h8']){const score=parseScore(x[h]);const u=x[h+'unknown'];if(!Number.isInteger(u)||u<0||(!score&&u!==0)||(score&&u>score.trials-score.success))throw Error('无法判定数与成绩不一致');}
 if(x.h30!==undefined||x.h30unknown!==undefined){if(!safeText(x.h30,1200))throw Error('字段无效：h30');const score=parseScore(x.h30),u=x.h30unknown;if(!Number.isInteger(u)||u<0||(!score&&u!==0)||(score&&u>score.trials-score.success))throw Error('无法判定数与成绩不一致');}
 if((x.h4||x.h8||x.h30)&&(!x.path.trim()||x.step<1))throw Error('评测成绩必须对应明确的权重路径和训练步数');
 if((x.h4||x.h8||x.h30)&&!x.protocol.trim())throw Error('填写成绩时必须说明泛化、环境和验收条件');
 if(x.state==='results'&&!x.h4&&!x.h8&&!x.h30&&!x.target)throw Error('已有结果至少填写4步、8步或30步成绩');
 return x;
}
function parseIssue(issue){
 if(!issue||issue.pull_request||typeof issue.body!=='string'||issue.body.length>16000||!Number.isInteger(issue.number)||!issue.user?.login||!Number.isFinite(Date.parse(issue.updated_at)))return null;
 const labels=(issue.labels||[]).map(x=>typeof x==='string'?x:x.name);if(labels.includes('safelab-archived'))return null;
 const m=/```safelab-handoff\s*\n([\s\S]*?)\n```/.exec(issue.body);if(!m)return null;
 try{const edit=validateEdit(JSON.parse(m[1]));return {...edit,issue:issue.number,author:issue.user.login,updated:issue.updated_at,url:'https://github.com/asimfish/safelab-handoff/issues/'+issue.number,trusted:['OWNER','MEMBER','COLLABORATOR'].includes(issue.author_association)||labels.includes('safelab-approved')};}catch{return null;}
}
// Scores never migrate into v1 by inference. Evidence and complete denominators are required.
const PROTOCOL='SafeLab-Eval-v1',CURRENT_PROTOCOL='SafeLab-Eval-v1.1';
const isRevoked=e=>e.metric_role==='rescored_v1.1_candidate';
const oracleFor=e=>e.oracle_version||(e.protocol_version===PROTOCOL?'strict-v1':null);
const admissionKeys=e=>['expert_replay','open_loop','render_multiframe','smoke20',...(e.protocol_version===CURRENT_PROTOCOL?['executor_parity']:[])];
function wilson95(success,n){
 if(!Number.isInteger(n)||n<1||!Number.isInteger(success)||success<0||success>n)return null;
 const z=1.959963984540054,p=success/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;
 return {low:Math.max(0,c-h),high:Math.min(1,c+h),confidence:0.95};
}
function formalIssues(e){
 const issues=[],count=x=>Number.isInteger(x)&&x>=0;
 const conserved=x=>x&&count(x.success)&&count(x.unknown)&&x.success+x.unknown<=x.trials&&(!Object.hasOwn(x,'failure')||count(x.failure)&&x.success+x.failure+x.unknown===x.trials);
 if(![PROTOCOL,CURRENT_PROTOCOL].includes(e.protocol_version)||!['A','B'].includes(e.stage))issues.push('非正式协议阶段A/B');
 if(e.protocol_version===CURRENT_PROTOCOL?e.oracle_version!=='placement-v1.1':e.oracle_version!=null&&!['strict-v1','strict-fdvel-v1'].includes(e.oracle_version))issues.push('判定版本不匹配');
 if(oracleFor(e)==='strict-fdvel-v1'&&(!safeText(e.paired_evaluation_id,300)||!e.paired_evaluation_id?.trim()||e.paired_evaluation_id===e.id))issues.push('FD缺少同批轨迹paired_evaluation_id');
 if(![4,8].includes(e.horizon))issues.push('仅4/8步');
 if(['assisted','rescored_v1.1_candidate'].includes(e.metric_role)||/诊断/.test(e.kind||''))issues.push('诊断或辅助指标');
 const n=e.stage==='B'?500:100;
 if(e.evaluation_started===false||e.trials!==n||e.completed!==n||!conserved(e))issues.push('未完成或分母无效');
 if(e.topology?.num_envs_actual!==1||!Number.isInteger(e.topology?.procs_per_gpu)||e.topology.procs_per_gpu<1||!safeText(e.topology?.gpu_type,150)||!e.topology?.gpu_type?.trim())issues.push('拓扑待核验');
 if(e.preprocess_resize?.implementation!=='training_tensor'||e.preprocess_resize?.mode!=='bilinear'||e.preprocess_resize?.antialias!==true||!e.preprocess_resize?.source)issues.push('预处理未对齐');
 if(!e.condition_version||!/^sha256:[a-f0-9]{64}$/.test(e.scene_list_hash||''))issues.push('条件版本或场景哈希缺失');
 const splits=e.lr_split,lr=splits&&[splits.left,splits.right];
 if(!lr||lr.some(x=>!x||x.trials!==n/2||!conserved(x))||lr.reduce((a,x)=>a+x.success,0)!==e.success||lr.reduce((a,x)=>a+x.unknown,0)!==e.unknown)issues.push('左右拆分不完整');
 const seeds=e.seed_results;
 if(!Array.isArray(seeds)||seeds.length!==(e.stage==='B'?5:1)||new Set(seeds.map(x=>x.seed)).size!==seeds.length||!seeds.some(x=>x.seed===0)||seeds.some(x=>!count(x.seed)||x.trials!==100||!conserved(x))||seeds.reduce((a,x)=>a+x.success,0)!==e.success||seeds.reduce((a,x)=>a+x.unknown,0)!==e.unknown)issues.push('逐seed记录不完整');
 const validTrials=e.trials-e.unknown,hist=Object.entries(e.phase_hist||{}),total=hist.reduce((a,[,v])=>a+v,0),mean=validTrials>0?hist.reduce((a,[k,v])=>a+Number(k)*v,0)/validTrials:null;
 if(!e.phase_hist||typeof e.phase_hist!=='object'||Array.isArray(e.phase_hist)||hist.some(([k,v])=>!/^\d+$/.test(k)||!count(v))||total!==validTrials||(validTrials===0?e.mean_phase!==null:!Number.isFinite(e.mean_phase)||Math.abs(mean-e.mean_phase)>1e-6))issues.push('阶段统计不完整');
 if(e.unknown_reasons!=null){const reasons=Object.values(e.unknown_reasons);if(typeof e.unknown_reasons!=='object'||Array.isArray(e.unknown_reasons)||reasons.some(v=>!count(v))||reasons.reduce((a,v)=>a+v,0)!==e.unknown)issues.push('unknown原因计数不守恒');}
 if(!admissionKeys(e).every(k=>e.admission?.[k]?.passed===true&&e.admission[k].report))issues.push('准入证据缺失');
 return issues;
}
function formalComparisons(board,view='auto'){
 const groups=new Map(),index=evaluationIndex(board),placementTasks=new Set(index.filter(e=>e.protocol_version===CURRENT_PROTOCOL&&!formalIssues(e).length).map(e=>e.task));
 for(const e of index){
  if(formalIssues(e).length||fdPairIssues(e,index).length)continue;
  const desired=view==='auto'?(placementTasks.has(e.task)?'placement-v1.1':'strict-v1'):view;
  if(oracleFor(e)!==desired)continue;
  // Dataset, view, scene list, stage and condition are separate comparison cohorts.
  const cohort=JSON.stringify([e.protocol_version,oracleFor(e),e.task,e.dataset,e.camera,e.stage,e.condition_version,e.scene_list_hash,e.metric||'original_physical',e.preprocess_resize]);
  const key=cohort+'|'+e.method,prior=groups.get(key);
  if(!prior||e.success/e.trials>prior.success/prior.trials||e.success/e.trials===prior.success/prior.trials&&(e.mean_phase??-Infinity)>(prior.mean_phase??-Infinity))groups.set(key,{...e,wilson95:wilson95(e.success,e.trials),valid_trials:e.trials-e.unknown,sensitivity_upper:(e.success+e.unknown)/e.trials});
 }
 return [...groups.values()].sort((a,b)=>Number(a.task)-Number(b.task)||a.dataset.localeCompare(b.dataset)||a.method.localeCompare(b.method)||a.stage.localeCompare(b.stage));
}
// Parallel oracle columns are rollout-linked, never inferred from a shared scene roster.
function sameRolloutConfig(a,b){
 const fields=['trials','rowKey','task','dataset','camera','checkpoint','horizon','stage','condition_version','scene_list_hash'];
 return fields.every(k=>a[k]===b[k])&&JSON.stringify(a.topology)===JSON.stringify(b.topology)&&JSON.stringify(a.preprocess_resize)===JSON.stringify(b.preprocess_resize)&&JSON.stringify((a.seed_results||[]).map(x=>[x.seed,x.trials]))===JSON.stringify((b.seed_results||[]).map(x=>[x.seed,x.trials]));
}
function fdPairIssues(e,index){
 if(oracleFor(e)!=='strict-fdvel-v1')return [];
 const other=index.find(x=>x.id===e.paired_evaluation_id);
 return other&&['strict-v1','placement-v1.1'].includes(oracleFor(other))&&sameRolloutConfig(e,other)?[]:['FD配对不存在或配置不一致'];
}
function oracleComparisons(board){
 const kinds=['strict-v1','strict-fdvel-v1','placement-v1.1'],all=evaluationIndex(board).filter(e=>[PROTOCOL,CURRENT_PROTOCOL].includes(e.protocol_version)&&['A','B'].includes(e.stage)&&kinds.includes(oracleFor(e))),ids=new Map(all.map(e=>[e.id,e])),parent=new Map(all.map(e=>[e.id,e.id])),invalid=new Set();
 const root=id=>{while(parent.get(id)!==id)id=parent.get(id);return id;};
 for(const e of all){const ref=e.paired_evaluation_id||(oracleFor(e)==='placement-v1.1'?e.source_evaluation_id:null),other=ids.get(ref);
  if(ref&&other&&ref!==e.id&&sameRolloutConfig(e,other)&&oracleFor(e)!==oracleFor(other))parent.set(root(e.id),root(other.id));
  else if(oracleFor(e)==='strict-fdvel-v1')invalid.add(e.id);
 }
 const groups=new Map();
 for(const e of all){const key=root(e.id);if(!groups.has(key))groups.set(key,{...e,oracles:{}});const g=groups.get(key),kind=oracleFor(e),issues=formalIssues(e);if(invalid.has(e.id))issues.push('FD配对不存在或配置不一致');const value={...e,score_eligible:issues.length===0,comparison_issues:issues,wilson95:wilson95(e.success,e.trials)};
  // Multiple rows for one oracle are ambiguous: expose the conflict instead of picking best.
  if(g.oracles[kind])g.oracles[kind]={...value,score_eligible:false,comparison_issues:['同批次同口径存在多行，需明确来源']};else g.oracles[kind]=value;
 }
 return [...groups.values()];
}
// Revoked drift-candidate records remain in the raw archive only.
function rescoredCandidates(){return [];}
function resultFor(evaluations,horizon){
 let rows=evaluations.filter(e=>e.protocol_version!==CURRENT_PROTOCOL&&oracleFor(e)!=='strict-fdvel-v1'&&!['assisted','rescored_v1.1_candidate'].includes(e.metric_role)&&e.formal_score_eligible!==false&&e.metric_role!=='assisted'&&e.horizon===horizon&&e.success!==null&&e.completed===e.trials&&!/诊断/.test(e.kind));
 const priority=Math.max(...rows.map(e=>e.display_priority||0));rows=rows.filter(e=>(e.display_priority||0)===priority);
 if(!rows.length)return null;
 const five=rows.filter(e=>e.kind==='自主闭环 · 5-seed');
 const chosen=five.length?five:[rows.find(e=>e.id.startsWith('single-')||e.id.endsWith('-single'))||rows.find(e=>e.kind==='自主闭环')||rows[0]];
 return {success:chosen.reduce((s,e)=>s+e.success,0),trials:chosen.reduce((s,e)=>s+e.trials,0),unknown:chosen.reduce((s,e)=>s+e.unknown,0),label:five.length?five.length+'轮汇总':chosen[0].result_label||chosen[0].kind,protocol:chosen[0].protocol,rows:chosen,reported:false};
}
function progressFor(evaluations,horizon){
 const rows=evaluations.filter(e=>e.protocol_version!==CURRENT_PROTOCOL&&oracleFor(e)!=='strict-fdvel-v1'&&!['assisted','rescored_v1.1_candidate'].includes(e.metric_role)&&e.formal_score_eligible!==false&&e.metric_role!=='assisted'&&e.horizon===horizon&&e.success===null&&e.evaluation_started!==false&&Number.isInteger(e.completed)&&Number.isInteger(e.trials)&&e.trials>0&&e.completed>=0&&e.completed<=e.trials);
 return rows.sort((a,b)=>(b.display_priority||0)-(a.display_priority||0)||String(b.updated_at||'').localeCompare(String(a.updated_at||'')))[0]||null;
}
function buildBoard(data,edits=[]){
 const datasets=data.datasets.map(d=>({...d,task:TASKS.find(t=>t.versions.includes(d.id))?.id||'other',version:VERSIONS[d.id]||d.label}));
 const rows=[];
 for(const record of data.records){
  for(const w of record.weights.length?record.weights:[null]){
   const evaluations=w?data.evaluations.filter(e=>!isRevoked(e)&&e.record===record.id&&e.checkpoint===w.step):[];
   const h4=resultFor(evaluations,4),h8=resultFor(evaluations,8),h30=resultFor(evaluations,30);
   const pending=evaluations.filter(e=>e.success===null&&e.evaluation_started!==false&&e.metric_role!=='rescored_v1.1_candidate');
   let state=pending.length?'evaluating':h4||h8||evaluations.some(e=>e.success!==null)?'results':/历史.*核验/.test(w?.status||'')?'verify':w?(w.path?'untested':'verify'):/训练中/.test(record.delivery)?'training':'verify';
   rows.push({key:key(record.id,w?.step||0),record,dataset:record.dataset,task:datasets.find(d=>d.id===record.dataset)?.task||(['3','5','7','10'].includes(record.task_hint)?record.task_hint:'other'),camera:CAMERAS[record.camera]?record.camera:'unknown',method:record.method,step:w?.step||0,path:w?.path||'',doc:record.doc||'',state,h4,h8,h30,pending,evaluations,owner:record.checkpoint_issues?.find(i=>i.checkpoint===w?.step&&i.evaluation_owner)?.evaluation_owner||record.owner||'未指定',issue_bindings:(record.checkpoint_issues||[]).filter(i=>i.checkpoint===w?.step),run:record.training?.executor_run||'',note:record.note||'',updated:data.updated_at,availability:w?.availability||record.delivery,training:record.training||{},source:record.source,shared:null});

  }
 }
 const ordered=edits.filter(e=>e.trusted).sort((a,b)=>a.updated.localeCompare(b.updated)||a.issue-b.issue);
 const bindings=data.records.flatMap(r=>(r.checkpoint_issues||[]).map(i=>({...i,record:r.id})));
 for(const raw of ordered){
  if(bindings.some(i=>i.number===raw.issue&&i.duplicate_of))continue;
  const binding=bindings.find(i=>i.number===raw.issue&&i.issue_updated_at===raw.updated);
  const e=binding?{...raw,target:key(binding.record,binding.checkpoint)}:raw;
  if(binding&&!e.h4&&!e.h8&&!e.h30){
   const canonical=rows.find(r=>r.record?.id===binding.record&&r.step===binding.checkpoint);
   if(canonical){Object.assign(canonical,{owner:binding.evaluation_owner||canonical.owner,shared:e});continue;}
  }
  const resolved=data.handoff_resolutions?.find(r=>r.issue===e.issue&&r.issue_updated_at===e.updated);
  if(resolved?.delivery_document===e.path&&resolved.checkpoint===e.step&&!e.h4&&!e.h8&&!e.h30){
   const canonical=rows.find(r=>r.record?.id===resolved.record&&r.step===e.step&&r.task===e.task&&r.dataset===e.dataset&&r.camera===e.camera&&r.method===e.method);
   if(canonical){Object.assign(canonical,{owner:e.owner||canonical.owner,shared:e});continue;}
  }
  if(resolved&&!e.path&&!e.h4&&!e.h8&&!e.h30&&data.records.some(r=>r.id===resolved.record&&r.weights.some(w=>w.path)))continue;
  let row=e.target?rows.find(r=>r.key===e.target):rows.find(r=>r.key==='issue-'+e.issue||e.path&&r.path===e.path&&r.dataset===e.dataset&&r.camera===e.camera&&r.method===e.method&&r.step===e.step);
  if(e.target&&!row)continue;
  const existingDataset=datasets.find(d=>d.id===e.dataset);
  if(existingDataset&&existingDataset.task!==e.task)continue;
  // Edits to evaluated identities create a new weight; original evidence stays attached.
  if(row&&(row.task!==e.task||row.dataset!==e.dataset||row.camera!==e.camera||row.method!==e.method||row.step!==e.step||row.path&&e.path!==row.path)){
   if(!row.path&&!row.evaluations.length){Object.assign(row,{dataset:e.dataset,task:e.task,camera:e.camera,method:e.method,step:e.step,path:e.path});}
   else row=rows.find(r=>r.key==='issue-'+e.issue)||null;
  }
  if(existingDataset&&e.data_path)existingDataset.path=e.data_path;
  if(!existingDataset&&e.dataset!=='unknown')datasets.push({id:e.dataset,label:e.version,version:e.version,task:e.task,path:e.data_path,episodes:null,frames:null,note:'团队新增版本，数据规模待核对',camera:e.camera});
  if(!row){row={key:'issue-'+e.issue,record:null,dataset:e.dataset,task:e.task,camera:e.camera,method:e.method,step:e.step,path:e.path,doc:e.doc,evaluations:[],pending:[],training:{},availability:'团队新增交付',source:'GitHub共享交接单',h4:null,h8:null,h30:null};rows.push(row);}
  Object.assign(row,{state:e.state,owner:e.owner||'未指定',doc:e.doc,run:e.run,note:e.note,updated:e.updated,shared:e});
  for(const h of ['h4','h8','h30'])if(e[h])row[h]={...parseScore(e[h]),unknown:e[h+'unknown'],label:'团队填报',protocol:e.protocol,rows:[],reported:true};
 }
 return {datasets,diagnostics:(data.diagnostics||[]).filter(e=>!isRevoked(e)),rows:rows.filter(r=>r.path||r.step>0&&r.doc||!rows.some(other=>other!==r&&other.path&&other.dataset===r.dataset&&other.camera===r.camera&&other.method===r.method))};
}
function issueBody(edit){validateEdit(edit);return '## SafeLab 共享交接记录\n\n提交后回到面板点击「同步更新」。修改本单请保留下面的数据块。不要填写密码、Token 或私钥。\n\n```safelab-handoff\n'+JSON.stringify(edit,null,2)+'\n```';}
function evaluationIndex(board){
 const index=[];
 for(const row of board.rows){
  for(const e of row.evaluations.filter(e=>!isRevoked(e)))index.push({...e,rowKey:row.key,task:row.task,camera:row.camera,method:row.method,phase:e.metric_role==='rescored_v1.1_candidate'?'diagnostic':e.success===null?'progress':formalIssues(e).length?'legacy':'formal'});
  for(const horizon of [4,8,30]){const score=row['h'+horizon];if(score?.reported)index.push({id:'shared-'+row.shared.issue+'-'+horizon,rowKey:row.key,task:row.task,dataset:row.dataset,camera:row.camera,method:row.method,checkpoint:row.step,horizon,success:score.success,trials:score.trials,unknown:score.unknown,completed:score.trials,status:'团队填报',kind:'团队共享评测',phase:'reported',protocol:score.protocol,source:row.shared.url,report_url:row.shared.url,note:'团队填报成绩；原始验收证据请见共享交接单。'});}
 }
 for(const d of board.diagnostics.filter(e=>!isRevoked(e))){
  const dataset=board.datasets.find(x=>x.id===d.dataset),row=board.rows.find(r=>r.record?.id===d.record&&r.step===d.checkpoint);
  index.push({...d,phase:'diagnostic',rowKey:row?.key||null,task:dataset?.task||'other',camera:d.camera||row?.camera||'unknown'});
 }
 return index;
}
function pendingRows(board){return board.rows.filter(r=>r.path&&r.state==='untested');}
function handoffPacket(board,row){const d=board.datasets.find(d=>d.id===row.dataset);return {task:row.task,method:row.method,dataset_version:d?.version||row.dataset,training_dataset:d?.path||row.shared?.data_path||null,camera:row.camera,checkpoint_step:row.step,checkpoint_path:row.path,delivery_document:row.doc||null,training_run:row.run||null,normalization_hash:row.record?.norm||null,training_config:row.training,owner:row.owner,execution_horizons_to_test:[4,8],test_protocol:'请根据该数据版本的交付文档确认泛化、控制频率和成功验收条件，不沿用其他版本',availability:row.availability,shared_handoff:row.shared?.url||null};}
const api={fdPairIssues,oracleComparisons,sameRolloutConfig,PROTOCOL,CURRENT_PROTOCOL,isRevoked,oracleFor,admissionKeys,wilson95,formalIssues,formalComparisons,rescoredCandidates,STATES,CAMERAS,TASKS,VERSIONS,key,parseScore,validateEdit,parseIssue,resultFor,progressFor,buildBoard,issueBody,evaluationIndex,pendingRows,handoffPacket};
if(typeof module!=='undefined')module.exports=api;root.HandoffModel=api;
})(typeof window==='undefined'?globalThis:window);
