'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto'),zlib=require('node:zlib');
const root='reports/task7-v12-relaxed-20261105/history_math/recovered_after_v1/',read=p=>JSON.parse(fs.readFileSync(p)),hash=b=>crypto.createHash('sha256').update(b).digest('hex'),sha=p=>hash(fs.readFileSync(p));
const publication=read(root+'summary.json'),sources=[];
for(const c of publication.cohorts){
 assert.equal(sha(c.summary.file),c.summary.sha256);const s=read(c.summary.file),dir=c.summary.file.slice(0,c.summary.file.lastIndexOf('/')+1),buffers=[];
 for(const f of s.source_index.chunks){const b=fs.readFileSync(dir+f.file);assert.equal(b.length,f.bytes);assert.equal(hash(b),f.sha256);const d=zlib.gunzipSync(b,{maxOutputLength:131072});assert.equal(d.length,f.decoded_bytes);assert.equal(hash(d),f.decoded_sha256);buffers.push(d);}
 const original=Buffer.concat(buffers);assert.equal(original.length,s.source_index.bytes);assert.equal(hash(original),s.source_index.sha256);sources.push({cohort:c,stats:s,index:JSON.parse(original)});
}
test('recovered original indices reconstruct exact original bytes and remain diagnostic contact math',()=>{
 assert.ok(sources.length>=3);let n=0;
 for(const {cohort,stats:s,index}of sources){assert.equal(index.expected,index.cached);assert.deepEqual(index.pending_readbacks,[]);assert.equal(index.records.length,s.actual_existing_case_n);assert.equal(s.actual_existing_case_n,cohort.n);assert.equal(s.original_small_receipts_full_byte_SHA_verified,cohort.n);assert.equal(s.formal_score_eligible,false);assert.equal(s.formal_placement_success,null);assert.equal(s.strict_original_reexecuted,false);assert.equal(s.canonical_v11_U,cohort.n);assert.equal(s.canonical_relaxed_U,cohort.n);n+=cohort.n;}
 assert.equal(n,publication.newly_processed_existing_historical_cases);assert.equal(n,publication.canonical_relaxed_U);assert.equal(publication.all_known_unique_case_inventory_n,n+2385+200);assert.equal(publication.global_pooled_SR,null);
});
test('recovery statistics preserve every explicit source verdict and all stage prefixes with unknown full denominators',()=>{
 for(const {stats:s,index}of sources)for(const g of s.groups){
  const rr=index.records.filter(r=>r.variant===g.variant&&r.horizon===g.horizon&&r.condition===g.condition);assert.equal(rr.length,g.n_actual_historical_cases);
  for(const name of ['v1.1','v1.2-relaxed']){
   const os=rr.map(r=>r.math_protocols[name]),m=g.math[name];for(const v of ['S','F','U'])assert.equal(m[v],os.filter(o=>o.verdict===v).length);assert.equal(m.S+m.F+m.U,rr.length);assert.equal(m.complete_verdict_SR,m.U?null:m.S/rr.length);
   const valid=os.filter(o=>o.verdict!=='U');assert.equal(m.mean_phase_n,valid.length);assert.equal(m.mean_phase_valid_closed_only,valid.length?valid.reduce((n,o)=>n+o.phase,0)/valid.length:null);
   for(let k=1;k<=7;k++){const statuses=os.map(o=>o.phase!=null&&o.phase>=k?'S':o.verdict==='F'?'F':'U'),z=m.per_stage[k];assert.equal(z.N,rr.length);for(const v of ['S','F','U'])assert.equal(z[v],statuses.filter(x=>x===v).length);}
  }
 }
});
test('recovered old cohorts supersede availability notes without modifying primary results or double counting',()=>{
 const data=read('data.json');assert.equal(data.evaluations.find(r=>r.id==='task7-eval-v11-A-original-mem0_30k-h8').success,5);assert.equal(data.evaluations.find(r=>r.id==='task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8').success,7);assert.equal(publication.main_data_evaluation_rows_changed,false);
 assert.equal(publication.source_identity_overlap_n,0);assert.equal(publication.full_raw_SHA_overlap_with_prior_n,0);assert.equal(publication.new_raw_NN_GPU_API_reads_calls,0);
 for(const f of Object.values(publication.sources))assert.equal(sha(f.file),f.sha256);
 assert.equal(sha('reports/task7-v12-relaxed-20261105/history_math/old-original-N1-coverage-v1.json'),'d48f083e9f49e2413e14515adcebbd5a9e8ace416646e344fe401ed41ee2dc76');
 assert.ok(Object.values(publication.sources).some(f=>f.sha256==='5e2bc3ba0e74b3948fa8ced389cb8269b82f5d28a2a3b153662810eb02c2e68e'));
});
