'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib'),B=require('../scripts/check-media-budget.cjs');
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const row=(t,frame)=>({t_sim:t,frame,subtask_index:0,completion_score:null,threshold:null,positive_count:null,switched:false,physical_phase:0,physical_events:[]});
function setup(run){const root=fs.mkdtempSync(path.join(os.tmpdir(),'safelab-media-gate-'));try{fs.mkdirSync(path.join(root,'media/frame_logs/10/run'),{recursive:true});fs.mkdirSync(path.join(root,'media/manifests/10'),{recursive:true});run(root);}finally{fs.rmSync(root,{recursive:true,force:true});}}
function log(root,name,value={schema_version:'safelab-frame-log-v1',case_id:'case',rows:[row(0,0),row(.1,1)]}){const bytes=Buffer.from(JSON.stringify(value)),wire=name.endsWith('.gz')?zlib.gzipSync(bytes):bytes;fs.writeFileSync(path.join(root,name),wire);return {url:'https://asimfish.github.io/safelab-handoff/'+name,bytes:wire.length,sha256:hash(wire),...(name.endsWith('.gz')?{encoding:'gzip',decoded_bytes:bytes.length,decoded_sha256:hash(bytes)}:{})};}
test('same-origin plain log is bound by bytes/SHA and counts toward complete snapshot budget',()=>setup(root=>{
 const name='media/frame_logs/10/run/case.json',asset=log(root,name),manifest='media/manifests/10/run.json';fs.writeFileSync(path.join(root,manifest),JSON.stringify({cases:[{case_id:'case',frame_log:asset}]}));const report=B.inspect(root,[name,manifest]);assert.equal(report.frame_logs,1);assert.equal(report.frame_log_bytes,asset.bytes);assert.ok(report.snapshot_bytes>report.frame_log_bytes);assert.throws(()=>B.inspect(root,[name,manifest],{...B.LIMITS,snapshot:1}),/budget/);assert.throws(()=>B.inspect(root,[name]),/Unreferenced/);
}));
test('frame-log URLs reject cross-origin, userinfo, query tokens and encoded traversal',()=>{
 for(const url of ['https://evil.example/media/frame_logs/10/a.json','https://asimfish.github.io/safelab-handoff/media/frame_logs/10/a.json?token=hidden','https://x@asimfish.github.io/safelab-handoff/media/frame_logs/10/a.json','https://asimfish.github.io/safelab-handoff/media/frame_logs/10/%2e%2e%2foutside.json'])assert.throws(()=>B.localLogPath(url));
 assert.equal(B.localLogPath('https://asimfish.github.io/safelab-handoff/media/frame_logs/10/run/a.json'),'media/frame_logs/10/run/a.json');
});
test('gzip verifies compressed and decoded identities and fails on excessive expansion',()=>setup(root=>{
 const name='media/frame_logs/10/run/case.json.gz',asset=log(root,name),entry=B.readLog(root,name);B.validateAsset(asset,entry);assert.throws(()=>B.validateAsset({...asset,sha256:'0'.repeat(64)},entry),/wire/);assert.throws(()=>B.validateAsset({...asset,decoded_sha256:'0'.repeat(64)},entry),/decoded/);assert.throws(()=>B.validateAsset({...asset,encoding:'identity'},entry),/encoding/);fs.writeFileSync(path.join(root,name),zlib.gzipSync(Buffer.alloc(B.LIMITS.asset+1,32)));assert.throws(()=>B.readLog(root,name));
}));
test('clock regressions, sampling-count contradictions and media symlinks fail',()=>setup(root=>{
 const name='media/frame_logs/10/run/case.json';log(root,name,{schema_version:'safelab-frame-log-v1',case_id:'case',rows:[row(0,0),row(0,1)]});assert.throws(()=>B.readLog(root,name),/clocks/);log(root,name,{schema_version:'safelab-frame-log-v1',case_id:'case',rows:[row(0,0)],sampling:{original_rows:1,retained_rows:2}});assert.throws(()=>B.readLog(root,name),/Sampling/);const link='media/frame_logs/10/run/link.json';fs.symlinkSync('case.json',path.join(root,link));assert.throws(()=>B.inspect(root,[link]),/regular/);
}));
