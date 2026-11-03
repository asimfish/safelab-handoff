import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const BASE=process.env.SAFELAB_QA_BASE_URL||'http://127.0.0.1:8871/';
const R=process.cwd(),Q=path.join(R,'.qa');fs.mkdirSync(Q,{recursive:true});
const browser=spawn(process.env.SAFELAB_CHROME_BIN||'/usr/bin/google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--remote-allow-origins=*','--remote-debugging-port=0','--user-data-dir='+'/dev/shm/safelab_handoff_browser_'+process.pid+'_'+Date.now(),'about:blank'],{stdio:['ignore','ignore','pipe']});
let stderr='';browser.stderr.on('data',b=>{stderr+=b.toString();});browser.on('exit',(code,signal)=>{fs.writeFileSync(path.join(Q,'chrome_last_exit.json'),JSON.stringify({code,signal,stderr:stderr.slice(-12000)}));});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let ws;const errors=[],checks=[];
try{
 let endpoint;
 for(let i=0;i<Math.min(2400,Math.max(600,Math.ceil((Number(process.env.SAFELAB_CHROME_STARTUP_MS)||30000)/50)));i++){const m=stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(m){endpoint=m[1];break;}await sleep(50);}
 if(!endpoint){fs.writeFileSync(path.join(Q,'chrome_startup_stderr.txt'),stderr);throw Error('Chrome debug endpoint unavailable: '+stderr.slice(-800));}
 const port=new URL(endpoint).port;
 const target=await (await fetch('http://127.0.0.1:'+port+'/json/new?'+BASE,{method:'PUT'})).json();
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
 let id=0;const pending=new Map();ws.addEventListener('close',()=>{for(const p of pending.values())p.reject(Error('Chrome CDP closed: '+stderr.slice(-600)));pending.clear();});
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text+' '+(m.params.exceptionDetails.exception?.description??''));});
 const cmd=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});
 const run=async expression=>{const r=await cmd('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const assert=(yes,label)=>{if(!yes)throw Error('QA failed: '+label);checks.push(label);};
 await cmd('Runtime.enable');await cmd('Page.enable');
 await cmd('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 for(let i=0;i<600;i++){if(await run('!!document.querySelector("#rows [data-row]")'))break;await sleep(100);}
 assert(await run('!!document.querySelector("#rows [data-row]")'),'dashboard loaded before fixture injection');


 const fixture={id:'ui-unknown-fixture',record:'3-v13-mem0',dataset:'3-v13',method:'Mem-0',checkpoint:30000,horizon:8,protocol_version:'SafeLab-Eval-v1',stage:'A',success:3,trials:100,unknown:2,completed:100,kind:'自主闭环',protocol:'UI fixture only',topology:{num_envs_actual:1,procs_per_gpu:2,gpu_type:'Pro6000'},preprocess_resize:{implementation:'training_tensor',mode:'bilinear',antialias:true,source:'fixture'},condition_version:'original-v1',scene_list_hash:'sha256:'+'a'.repeat(64),lr_split:{left:{trials:50,success:1,unknown:1},right:{trials:50,success:2,unknown:1}},seed_results:[{seed:0,trials:100,success:3,unknown:2}],mean_phase:9/98,phase_hist:{0:95,3:3},admission:Object.fromEntries(['expert_replay','open_loop','render_multiframe','smoke20'].map(k=>[k,{passed:true,report:'fixture-only'}]))};
 await run('shared=[];data=structuredClone(data);data.evaluations=['+JSON.stringify(fixture)+'];rebuild()');
 assert(await run('document.querySelector(".formal-section tbody tr").textContent.includes("3.0%")'),'success uses full100 denominator');
 assert(await run('document.querySelector(".formal-section tbody tr").textContent.includes("unknown 2")'),'unknown count shown');
 assert(await run('document.querySelector(".sensitivity-upper").textContent.includes("5.0%")'),'unknown-all-success5percent sensitivity bound shown');
 assert(await run('document.querySelector(".formal-section tbody tr").textContent.includes("有效 98/100")'),'valid phase count excludes unknown');
 await run('data.evaluations[0].phase_hist={0:97,3:3};rebuild()');
 assert(await run('!document.querySelector(".sensitivity-upper")'),'invalid phase total excluded from comparison');
 const all={...fixture,success:0,unknown:100,mean_phase:null,phase_hist:{},lr_split:{left:{trials:50,success:0,unknown:50},right:{trials:50,success:0,unknown:50}},seed_results:[{seed:0,trials:100,success:0,unknown:100}]};
 await run('data.evaluations=['+JSON.stringify(all)+'];rebuild()');
 assert(await run('document.querySelector(".formal-section tbody tr").textContent.includes("无有效轨迹")'),'all unknown renders absent mean without crash');
 assert(await run('document.querySelector(".sensitivity-upper").textContent.includes("100.0%")'),'all-unknown sensitivity upper100percent');
 const candidate={...fixture,id:'ui-revoked-candidate',stage:'diagnostic',metric_role:'rescored_v1.1_candidate',success:99};
 const placement={...fixture,id:'ui-placement-fixture',protocol_version:'SafeLab-Eval-v1.1',oracle_version:'placement-v1.1',success:30,phase_hist:{0:68,3:30},mean_phase:90/98,lr_split:{left:{trials:50,success:15,unknown:1},right:{trials:50,success:15,unknown:1}},seed_results:[{seed:0,trials:100,success:30,unknown:2}],admission:{...fixture.admission,executor_parity:{passed:true,report:'fixture-only'}}};
 await run('data.evaluations=['+JSON.stringify(fixture)+','+JSON.stringify(candidate)+','+JSON.stringify(placement)+'];metricView="auto";rebuild()');
 assert(await run('document.querySelector("#metric-view").value==="auto"&&document.querySelector(".formal-section tbody tr").textContent.includes("30.0%")'),'auto task view prefers validated placement result');
 assert(await run('!M.evaluationIndex(board).some(e=>e.id==="ui-revoked-candidate")&&![...document.querySelector("#metric-view").options].some(o=>o.value==="v1.1-candidate")'),'revoked drift candidate has no table entry or selector');
 await run('document.querySelector("#metric-view").value="strict-v1";document.querySelector("#metric-view").dispatchEvent(new Event("change"))');
 assert(await run('document.querySelector(".formal-section tbody tr").textContent.includes("3.0%")&&!document.querySelector(".formal-section tbody tr").textContent.includes("30.0%")'),'strict comparison retains original score without pooling');
 await run('document.querySelector("#metric-view").value="placement-v1.1";document.querySelector("#metric-view").dispatchEvent(new Event("change"))');
 assert(await run('document.querySelector(".formal-section tbody tr").textContent.includes("30.0%")&&document.querySelector(".formal-section tbody tr").textContent.includes("placement-v1.1")'),'explicit placement view labels new oracle');
 assert(await run('document.querySelector("#checkpoint-coverage").textContent.includes("v1.1")&&!![...document.querySelectorAll("[data-coverage-state]")].some(e=>e.dataset.coverageState==="未开始")'),'v1.1 coverage lists missing configuration states');
 assert(errors.length===0,'no uncaught exceptions');
 fs.writeFileSync(path.join(Q,'UNKNOWN_BROWSER_QA.json'),JSON.stringify({passed:true,checks,errors,at:new Date().toISOString()},null,2));console.log(JSON.stringify({passed:true,checks,errors}));
}finally{if(ws)ws.close();browser.kill('SIGTERM');}
