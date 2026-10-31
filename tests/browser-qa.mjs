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
 for(let i=0;i<100;i++){if(await run('!!document.querySelector("#rows [data-row]")'))break;await sleep(100);}


 assert(await run('document.querySelectorAll("#main table").length===1&&!document.querySelector("aside")'),'one table only, no sidebar');
 assert(await run('document.querySelectorAll("#rows [data-row]").length===board.rows.length'),'every training and weight entry present in one table');
 assert(await run('document.querySelector(\'[data-row="3-v13-ours@30000"]\').innerText.includes("24.0%")&&document.querySelector(\'[data-row="3-v13-pi05@30000"]\').innerText.includes("0.0%")'),'TTC and pi0.5 real scores visible in their rows');
 assert(await run('document.querySelector(\'[data-row="3-latest-chest@30000"]\').querySelectorAll(".score").length===0'),'untested chest never inherits third person score');
 assert(await run('document.querySelector(\'[data-row="3-v13-ours@30000"] [data-copy]\').dataset.copy.includes("safelab_mem")'),'training dataset full path can be copied');
 fs.writeFileSync(path.join(Q,'single-table.png'),Buffer.from((await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await run('document.querySelector("#filter-task").value="5";document.querySelector("#filter-task").dispatchEvent(new Event("change"))');
 assert(await run('document.querySelectorAll("#rows [data-row]").length===3'),'all five-task old and new dataset weights filter together');
 await run('document.querySelector(\'[data-detail="5-fixed-mem0@30000"]\').click()');
 assert(await run('document.querySelector("#detail-body").innerText.includes("1/2")&&document.querySelector("#detail-body").innerText.includes("非正式成绩")'),'training input diagnosis retained behind row details, no formal score pollution');
 await run('document.querySelector("#detail").close();document.querySelector("#filter-task").value="10";document.querySelector("#filter-task").dispatchEvent(new Event("change"))');
 assert(await run('document.querySelector(\'[data-row="10-ours-training-unconfirmed@0"]\').innerText.includes("训练中（待确认）")&&!document.querySelector(\'[data-row="10-ours-training-unconfirmed@0"]\').querySelector(".score")'),'ten-task TTC possibly training, no invented checkpoint or results');
 await run('document.querySelector(\'[data-edit="10-ours-training-unconfirmed@0"]\').click()');
 assert(await run('document.querySelector("#editor").open&&document.querySelector(\'[name="state"]\').value==="training"&&document.querySelector(\'[name="step"]\').value==="0"&&!document.querySelector(\'[name="path"]\').disabled'),'training placeholder editable before checkpoint exists');
 await run('window.open=url=>{window.savedIssueURL=String(url)};document.querySelector("#edit-form").requestSubmit()');
 assert(await run('new URL(window.savedIssueURL).searchParams.get("body").includes("training")&&new URL(window.savedIssueURL).searchParams.get("body").includes("10-ours-training-unconfirmed@0")'),'shared editor accepts unfinished training without path');
 await run('document.querySelector("#editor").close();document.querySelector("#filter-task").value="all";document.querySelector("#filter-task").dispatchEvent(new Event("change"));document.querySelector(\'[data-edit="3-v13-ours@30000"]\').click()');
 assert(await run('!document.querySelector(\'[name="path"]\').disabled&&!document.querySelector(\'[name="data_path"]\').disabled'),'weight and training dataset locations editable');await run('document.querySelector("#editor").close()');
 for(let i=0;i<250;i++){if(await run('!document.querySelector("#sync").disabled'))break;await sleep(100);}
 await run(`window.originalFetch=window.fetch;window.nextSnapshot=JSON.parse(JSON.stringify(data));window.nextSnapshot.evaluations.find(e=>e.id==='sr-v13-mem0-4').success=41;window.fetch=async url=>String(url).startsWith('data.json')?{ok:true,json:async()=>window.nextSnapshot}:{ok:true,json:async()=>[]};document.querySelector('#sync').click()`);await sleep(200);
 assert(await run('document.querySelector(\'[data-row="3-v13-mem0@30000"]\').innerText.includes("41.0%")'),'refresh updates baseline and shared data in the same table');
 await run('document.querySelector(\'[data-detail="3-v13-mem0@30000"]\').click()');assert(await run('document.querySelector("#detail-body").innerText.includes("41/100")'),'table and history detail agree after refresh');await run('document.querySelector("#detail").close()');
 await run(`window.fetch=async url=>String(url).startsWith('data.json')?{ok:true,json:async()=>data}:({ok:true,json:async()=>[{number:999,body:HandoffModel.issueBody({schema:2,kind:'checkpoint',target:'',task:'3',dataset:'3-latest',version:'latest',data_path:'/data',camera:'chest',method:'<img src=x onerror=window.xss=1>',step:40000,path:'/weights/40k.pt',doc:'',owner:'Trainer',run:'',protocol:'',note:'<script>window.xss=1</script>',h4:'',h8:'',h4unknown:0,h8unknown:0,state:'untested'}),updated_at:'2026-10-31T10:00:00Z',user:{login:'trainer'},author_association:'COLLABORATOR',labels:[]}]});document.querySelector('#sync').click()`);await sleep(200);
 assert(await run('document.querySelector(\'[data-row="issue-999"]\').textContent.includes("<img")&&!document.querySelector(\'[data-row="issue-999"] img\')&&!window.xss'),'shared text never executes HTML');
 await run('window.fetch=window.originalFetch');
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await sleep(100);
 assert(await run('document.documentElement.scrollWidth<=innerWidth'),'mobile page contained, only table scrolls');
 assert(errors.length===0,'no uncaught page exceptions');
 const result={passed:true,checks,errors,at:new Date().toISOString()};fs.writeFileSync(path.join(Q,'BROWSER_QA.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{if(ws)ws.close();browser.kill('SIGTERM');}
