const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {validate}=require('./curve-contract.js');const source=JSON.parse(fs.readFileSync(path.join(__dirname,'frozen-data.json')));
test('every displayed task has exactly N real monotone SRk values',()=>{validate(source);const t=source.curves.find(c=>c.task===10&&c.method==='TTS-Memory');assert.equal(t.srk[9],0.5);});
test('truncated or missing curves fail explicitly rather than display undefined or zero-fill',()=>{const d=structuredClone(source);d.curves.find(c=>c.task===10&&c.method==='TTS-Memory').srk.pop();assert.throws(()=>validate(d),/expected 10 SR@k points/);const missing=structuredClone(source);missing.curves.pop();assert.throws(()=>validate(missing),/Expected one/);});

test('episode success points equal the same Table2 cells',()=>{const d=structuredClone(source);d.episode_curves[1].success_rate[2]=0;assert.throws(()=>validate(d),/episode curve differs from Table 2/);});
