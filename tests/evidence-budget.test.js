'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {inspect}=require('../scripts/check-media-budget.cjs');
test('report evidence over 200KB is rejected; frontend data is exempt',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'safelab-budget-'));
 try{
  fs.mkdirSync(path.join(root,'reports'));fs.writeFileSync(path.join(root,'reports/large.json'),Buffer.alloc(200001));
  assert.throws(()=>inspect(root,['reports/large.json']),/TOS reports-v1/);
  fs.writeFileSync(path.join(root,'reports/small.json'),Buffer.alloc(200000));
  assert.equal(inspect(root,['reports/small.json']).snapshot_bytes,200000);
  fs.writeFileSync(path.join(root,'data.json'),Buffer.alloc(250000));
  assert.equal(inspect(root,['data.json']).snapshot_bytes,250000);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
