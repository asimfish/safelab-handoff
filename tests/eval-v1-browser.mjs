import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const BASE=process.env.SAFELAB_QA_BASE_URL||'http://127.0.0.1:8770/';
const R=process.cwd(),Q=path.join(R,'.qa');fs.mkdirSync(Q,{recursive:true});
const browser=spawn('/usr/bin/google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--remote-allow-origins=*','--remote-debugging-port=0','--user-data-dir='+'/dev/shm/safelab_handoff_browser_'+process.pid+'_'+Date.now(),'about:blank'],{stdio:['ignore','ignore','pipe']});
let stderr='';browser.stderr.on('data',b=>{stderr+=b.toString();});browser.on('exit',(code,signal)=>{fs.writeFileSync(path.join(Q,'chrome_last_exit.json'),JSON.stringify({code,signal,stderr:stderr.slice(-12000)}));});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let ws;const errors=[],checks=[];
try{
 let endpoint;
 for(let i=0;i<600;i++){const m=stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(m){endpoint=m[1];break;}await sleep(50);}
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
 for(let i=0;i<100;i++){if(await run('!!document.querySelector("#rows [data-row]")'))break;await sleep(100);}


 assert(await run('document.querySelector(".formal-section")&&document.querySelector(".protocol-banner a")'),'protocol link and formal comparison section present');
 assert(await run('!document.querySelector("#history-section").open'),'legacy and diagnostics folded by default');
 assert(await run('document.querySelector(".formal-section").innerText.includes("尚无符合")'),'no legacy scores promoted to v1');
 assert(await run('document.querySelector(".formal-section").innerText.includes("v2_solver128")'),'attach comparability warning visible');
 assert(await run('document.querySelectorAll("#rows [data-row]").length===board.rows.length'),'all original training and weight entries retained');
 await run('document.querySelector("#history-section").open=true;document.querySelector(\'[data-detail="3-v13-mem0@30000"]\').click()');
 assert(await run('document.querySelector("#detail-body").textContent.includes("legacy")'),'detail labels original protocol as legacy');
 await run('document.querySelector("#detail").close()');
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await sleep(100);
 assert(await run('document.documentElement.scrollWidth<=innerWidth'),'mobile page contained');
 await cmd('Page.navigate',{url:new URL('eval-v1.html',BASE).href});
 for(let i=0;i<100;i++){if(await run('document.body.textContent.includes("8 回信")'))break;await sleep(50);}
 assert(await run('document.body.textContent.includes("0/25/50/75/100%")&&document.body.textContent.includes("48 卡")&&document.body.textContent.includes("8 回信")'),'complete protocol text includes input, resources and reply requirements');
 assert(errors.length===0,'no uncaught page exceptions');
 const result={passed:true,checks,errors,at:new Date().toISOString()};fs.writeFileSync(path.join(Q,'EVAL_V1_BROWSER_QA.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{if(ws)ws.close();browser.kill('SIGTERM');}
