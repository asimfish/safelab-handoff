'use strict';
// Materialize only maintainer-reviewed issue metadata; never infer a new weight identity.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const file=process.argv[2]||path.join(__dirname,'../data.json'),data=JSON.parse(fs.readFileSync(file)),before=structuredClone(data);
const bindings=data.checkpoint_issue_audit?.bindings;if(!Array.isArray(bindings)||!bindings.length)throw Error('Reviewed checkpoint binding registry missing; review required');
const restored=[];
for(const binding of bindings){
 const {record,identity,...metadata}=binding,r=data.records.find(r=>r.id===record);
 if(!r||!r.weights.some(w=>w.step===metadata.checkpoint))throw Error('Reviewed record/checkpoint missing: #'+metadata.number);
 for(const [key,value]of Object.entries(identity))if(Object.hasOwn(r,key)&&r[key]!==value)throw Error('Reviewed identity changed: #'+metadata.number+' '+key);else if(!Object.hasOwn(r,key))r[key]=value;
 const existing=data.records.flatMap(other=>(other.checkpoint_issues||[]).filter(i=>i.number===metadata.number).map(i=>({record:other.id,binding:i})));
 if(existing.length>1||existing.some(i=>i.record!==record||i.binding.checkpoint!==metadata.checkpoint))throw Error('Conflicting/moved issue binding: #'+metadata.number+'; review registry and canonical record');
 if(existing.length){for(const [key,value]of Object.entries(metadata))if(!Object.hasOwn(existing[0].binding,key))existing[0].binding[key]=value;}
 else{(r.checkpoint_issues??=[]).push(metadata);restored.push(metadata.number);}
}
// Every pre-existing scalar/object/array entry is preserved; only missing metadata is added.
function preserved(old,next){if(old&&typeof old==='object'){for(const key of Object.keys(old)){assert.ok(Object.hasOwn(next,key));preserved(old[key],next[key]);}}else assert.deepEqual(next,old);}
preserved(before,data);
for(const key of ['evaluations','diagnostics','campaigns','datasets'])assert.deepEqual(data[key],before[key]);
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');console.log(JSON.stringify({restored_bindings:restored,existing_values_unchanged:true,reviewed_registry_only:true}));
