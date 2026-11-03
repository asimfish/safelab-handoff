'use strict';
// A reviewed mapping, not automatic approval of arbitrary public issues.
const fs=require('node:fs'),M=require('../model');
const source=process.argv[2];if(!source)throw Error('Usage: node scripts/sync-checkpoint-issues.cjs reviewed-issues.json [--write]');
const mapping={1:'3-latest-chest',2:'5-pos-ours-aligned',3:'7-mem0-weak',4:'5-pos-mem0-weak',5:'mem0-ablated',7:'3-latest-pi05-issue7',8:'3-latest-pi05-issue7',9:'3-v13-mem0',10:'3-latest-third',11:'3-v13-ours',12:'3-v13-ours',13:'3-v13-pi05',14:'3-v13-pi05',15:'3-latest-chest',16:'ttc-aligned',17:'5-pos-ttc-aligned-weak',18:'7-ours-weak-aligned-issue18',19:'ttc-aligned-ablated',20:'10-ours-aligned',21:'10-mem0-weak',22:'ttc-aligned-ablated',23:'5-pos-pi05-issue23',24:'7-pi05-issue24',26:'10-ttc-aligned-weak-issue26',38:'3-v13-mem0',39:'7-mem0',40:'7-ours-trainresize',41:'7-aligned'};
const data=JSON.parse(fs.readFileSync('data.json')),before=structuredClone(data),issues=JSON.parse(fs.readFileSync(source));
const report=[];
for(const [number,id]of Object.entries(mapping)){
 const raw=issues.find(i=>i.number===+number),e=M.parseIssue(raw);if(!e)throw Error('Missing/invalid reviewed issue #'+number);
 let r=data.records.find(r=>r.id===id);
 const placeholder=r&&!r.weights.length;
 if(!r){r={id,task:e.task,dataset:e.dataset,camera:e.camera,method:e.method,delivery:'交付入口已登记，权重文件待核验',doc:e.doc||e.path,weights:[],training:{},note:e.note,source:'GitHub checkpoint issue #'+number};data.records.push(r);}
 if(placeholder)Object.assign(r,{task:e.task,dataset:e.dataset,camera:e.camera,method:e.method,doc:e.doc,delivery:'权重已交付',note:e.note,history_placeholder:false});
 r.task=e.task;
 const actual=e.path&&!/\.md(?:$|[?#])/i.test(e.path);
 let w=r.weights.find(w=>w.step===e.step);
 if(!w){w={step:e.step,path:actual?e.path:'',availability:actual?'issue登记的checkpoint':'交付文档已登记，checkpoint文件路径待核验'};r.weights.push(w);}
 else if(!w.path&&actual)w.path=e.path;
 const binding={number:+number,checkpoint:e.step,url:raw.html_url,state:raw.state,issue_updated_at:raw.updated_at,handoff_owner:e.owner,evaluation_owner:/T-\d+|agent|codex|claude/i.test(e.owner)?e.owner:null,delivery_path:e.path||e.doc,delivery_document:e.doc||(!actual?e.path:''),supplied_camera:e.camera,recorded_state:e.state};
 if(+number===8)binding.duplicate_of=7;
 r.checkpoint_issues=(r.checkpoint_issues||[]).filter(i=>i.number!==+number);r.checkpoint_issues.push(binding);
 r.weights.sort((a,b)=>a.step-b.step);
 report.push({issue:+number,record:id,checkpoint:e.step,duplicate_of:binding.duplicate_of||null,path_kind:w.path?'checkpoint':'delivery_document',issue_state:raw.state});
}
for(const r of data.records)if(!r.weights.length){r.history_placeholder=true;r.placeholder_reason='未能与具体checkpoint issue绑定；保留历史训练占位，不计入权重覆盖。';}
// These sections contain evidence and must remain byte-equivalent as JSON values.
for(const k of ['evaluations','diagnostics','campaigns','datasets'])if(JSON.stringify(before[k])!==JSON.stringify(data[k]))throw Error('Unrelated evidence modified: '+k);
const bindings=data.records.flatMap(r=>(r.checkpoint_issues||[]).map(i=>({record:r.id,identity:{task:r.task,dataset:r.dataset,camera:r.camera,method:r.method},...i})));
data.checkpoint_issue_audit={schema_version:1,bindings,checked_at:new Date().toISOString(),source:'GitHub issues, open and closed; explicit maintainer-reviewed mapping',issues:report,duplicate_policy:'Issue8 duplicates7; keep both issue references on one weight; do not close automatically.'};
if(process.argv.includes('--write'))fs.writeFileSync('data.json',JSON.stringify(data,null,2)+'\n');
console.log(JSON.stringify({write:process.argv.includes('--write'),records:data.records.length,checkpoint_issues:report.length,canonical_issues:report.filter(x=>!x.duplicate_of).length,issues:report},null,2));
