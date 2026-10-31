import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
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
 const target=await (await fetch('http://127.0.0.1:'+port+'/json/new?http://127.0.0.1:8770/',{method:'PUT'})).json();
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
 let id=0;const pending=new Map();ws.addEventListener('close',()=>{for(const p of pending.values())p.reject(Error('Chrome CDP closed: '+stderr.slice(-600)));pending.clear();});
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text+' '+(m.params.exceptionDetails.exception?.description??''));});
 const cmd=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});
 const run=async expression=>{const r=await cmd('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const assert=(yes,label)=>{if(!yes)throw Error('QA failed: '+label);checks.push(label);};
 await cmd('Runtime.enable');await cmd('Page.enable');
 await cmd('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 for(let i=0;i<100;i++){if(await run('!!document.querySelector(".camera-group")'))break;await sleep(100);}


 await run('location.hash="task/3"');await sleep(150);
 const category=await run('!!document.querySelector("#task-evaluations")&&document.querySelectorAll("#task-evaluations [data-evaluation]").length>=data.evaluations.filter(e=>e.dataset.startsWith("3-")).length');
 for(let i=0;i<250;i++){if(await run('!document.querySelector("#sync").disabled'))break;await sleep(100);}
 await run(`window.snapshotReads=0;window.freshSnapshot=JSON.parse(JSON.stringify(data));window.freshSnapshot.evaluations.find(e=>e.id==='sr-v13-mem0-4').success=41;window.fetch=async url=>String(url).startsWith('data.json')?(window.snapshotReads++,{ok:true,json:async()=>window.freshSnapshot}):({ok:true,json:async()=>[]});document.querySelector('#sync').click()`);
 for(let i=0;i<100;i++){if(await run('!document.querySelector("#sync").disabled'))break;await sleep(50);}
 const refreshed=await run('window.snapshotReads===1&&board.rows.find(r=>r.key==="3-v13-mem0@30000").h4.success===41');

 const go=async hash=>{await run('location.hash='+JSON.stringify(hash));await sleep(160);};
 await go('task/3/3-v13');
 const taskScore=await run(`document.querySelector('[data-row="3-v13-mem0@30000"]').innerText.includes('41.0')&&document.querySelector('[data-evaluation="sr-v13-mem0-4"]').innerText.includes('41/100')&&document.querySelector('[data-evaluation="single-v13-pi05-4"]').innerText.includes('0/100')`);
 await go('overview');const overviewScore=await run(`document.querySelector('[data-detail="3-v13-mem0@30000"]').innerText.includes('41.0')`);
 await run(`document.querySelector('[data-detail="3-v13-mem0@30000"]').click()`);const detailScore=await run(`document.querySelector('#detail-body').innerText.includes('41/100')`);await run(`document.querySelector('#detail').close()`);
 await go('matrix');const matrixStatus=await run(`document.querySelector('[data-matrix-version="3-v13"] [data-detail="3-v13-mem0@30000"]').innerText.includes('评测中')`);
 await go('task/5');const fiveDiagnostic=await run(`document.querySelector('[data-evaluation="five-training-input-4"]').innerText.includes('1/2')&&document.querySelector('[data-evaluation="five-training-input-4"]').innerText.includes('诊断试验')`);
 await go('task/7');const sevenDiagnostic=await run(`document.querySelector('[data-evaluation="seven-b-return-candidate"]').innerText.includes('2/12')&&document.querySelector('[data-evaluation="seven-b-return-candidate"]').innerText.includes('待核对')`);
 const checks={all_task_evaluations_visible:category,sync_reloads_snapshot:refreshed,task_score:taskScore,overview_score:overviewScore,detail_score:detailScore,matrix_status:matrixStatus,five_diagnostic:fiveDiagnostic,seven_diagnostic:sevenDiagnostic};
 console.log(JSON.stringify(checks));if(Object.values(checks).some(x=>!x))throw Error('Task classification consistency regression');
 fs.writeFileSync(path.join(Q,'CLASSIFICATION_CONSISTENCY.json'),JSON.stringify({passed:true,checks},null,2));

}finally{if(ws)ws.close();browser.kill('SIGTERM');}
