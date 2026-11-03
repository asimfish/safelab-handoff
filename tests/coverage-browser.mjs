import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const BASE=process.env.SAFELAB_QA_BASE_URL||'http://127.0.0.1:8872/';
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



 assert(await run('document.querySelectorAll("#checkpoint-coverage tbody tr").length===HandoffCoverage.checkpointCoverage(board).length'),'every physical checkpoint appears once');
 assert(await run("(()=>{const model=HandoffCoverage.checkpointCoverage(board).find(r=>r.issues.some(i=>i.number===1)),row=[...document.querySelectorAll(\"#checkpoint-coverage tbody tr\")].find(r=>[...r.querySelectorAll(\"a\")].some(a=>a.href.endsWith(\"/issues/1\")));return !!row&&row.textContent.includes(\"已关闭\")&&row.dataset.missingV1===String(model.missingV1)})()"),'closed issue1 status remains separate from actual v1 coverage');
 assert(await run('[...document.querySelectorAll("#checkpoint-coverage tbody tr")].filter(r=>r.querySelector(\'a[href$="/issues/7"]\')||r.querySelector(\'a[href$="/issues/8"]\')).length===1'),'duplicate7 and8 share exactly one row');
 assert(await run('HandoffCoverage.checkpointCoverage(board).every(model=>{const row=[...document.querySelectorAll("#checkpoint-coverage [data-checkpoint]")].find(r=>r.dataset.checkpoint===model.rowKey);return row&&(model.path?[...row.querySelectorAll("[data-copy]")].some(b=>b.dataset.copy===model.path)&&!row.textContent.includes("checkpoint路径待核验"):row.textContent.includes("checkpoint路径待核验"))})'),'checkpoint paths match evidence; document-only entries remain pending');
 assert(await run('!document.querySelector(\'[data-checkpoint="memoryvla@0"]\')&&document.querySelector(\'[data-row="memoryvla@0"]\')'),'unbound placeholder stays only in historical table');
 fs.writeFileSync(path.join(Q,'CHECKPOINT_COVERAGE.png'),Buffer.from((await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await run('document.querySelector("#coverage-filter").value="missing";document.querySelector("#coverage-filter").dispatchEvent(new Event("change"))');
 assert(await run('[...document.querySelectorAll("#checkpoint-coverage tbody tr")].every(r=>r.dataset.missingV1==="true")'),'missing-only view contains only highlighted checkpoints');
 assert(await run('document.querySelectorAll("#checkpoint-coverage tbody tr").length===HandoffCoverage.checkpointCoverage(board).filter(r=>r.missingV1).length'),'missing filter count matches coverage model');
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await sleep(100);
 assert(await run('document.documentElement.scrollWidth<=innerWidth'),'mobile document contained; table scrolls locally');
 assert(errors.length===0,'no uncaught exceptions');
 fs.writeFileSync(path.join(Q,'CHECKPOINT_COVERAGE_BROWSER_QA.json'),JSON.stringify({passed:true,checks,errors,at:new Date().toISOString()},null,2));console.log(JSON.stringify({passed:true,checks,errors}));
}finally{if(ws)ws.close();browser.kill('SIGTERM');}
