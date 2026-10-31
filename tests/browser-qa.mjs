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

 const go=async hash=>{await run('location.hash='+JSON.stringify(hash));await sleep(180);};
 assert(await run('document.querySelectorAll(".overview-table").length===4&&document.body.innerText.includes("44.0")'),'landing shows all tasks and method scores together');
 fs.writeFileSync(path.join(Q,'overview.png'),Buffer.from((await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await go('matrix');
 assert(await run(`document.querySelectorAll(".handoff-matrix thead th").length===8&&document.querySelectorAll('[data-matrix-version="3-latest"]').length===3`),'single handoff matrix includes seven methods and camera-specific version rows');
 assert(await run('document.querySelector(".handoff-matrix").innerText.includes("MemoryVLA")&&document.querySelector(".handoff-matrix").innerText.includes("训练中")&&document.querySelector(".handoff-matrix").innerText.includes("对齐削弱版")'),'matrix preserves unbound training and all supplied ablation columns');
 fs.writeFileSync(path.join(Q,'matrix.png'),Buffer.from((await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await run(`document.querySelector('.handoff-matrix [data-detail="3-v13-ours@20000"]').click()`);
 assert(await run('document.querySelector("#detail").open&&document.querySelector("#detail-body").innerText.includes("20,000")'),'matrix checkpoint opens its matching handoff details');
 await run('document.querySelector("#detail").close()');
 await go('coverage');
 assert(await run('document.querySelectorAll("#main tbody tr").length===8&&document.body.innerText.includes("58,148")&&document.body.innerText.includes("不是后台自动跟踪")'),'coverage page exposes eight session cutoffs and exact limits');
 await go('queue');
 assert(await run('document.querySelectorAll("[data-pending]").length===HandoffModel.pendingRows(board).length&&document.querySelectorAll("[data-packet]").length>0'),'global queue contains every delivered untested checkpoint with deployment packet');
 await go('task/3');
 assert(await run('document.querySelectorAll(".version-tabs a").length===3'),'three distinct data versions for task3');
 assert(await run('Array.from(document.querySelectorAll(".group-title h2")).some(e=>e.textContent==="第三人称")&&Array.from(document.querySelectorAll(".group-title h2")).some(e=>e.textContent==="胸部相机")'),'latest chest and third person kept separate');
 assert(await run('document.querySelector(\'[data-row="3-latest-chest@30000"]\').innerText.includes("尚无已核对结果")'),'chest does not inherit third person score');
 fs.writeFileSync(path.join(Q,'desktop.png'),Buffer.from((await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await go('task/3/3-v13');
 assert(await run('document.querySelector(\'[data-row="3-v13-mem0@30000"]\').innerText.includes("44.0")&&document.querySelector(\'[data-row="3-v13-mem0@30000"]\').innerText.includes("评测中")'),'same checkpoint shows labeled SR result and ongoing retest');
 assert(await run('document.querySelector(\'[data-row="3-v13-pi05@30000"]\').innerText.includes("0.0")'),'confirmed zero success stays a numeric result');
 await run('document.querySelector(\'[data-detail="3-v13-mem0@30000"]\').click()');
 assert(await run('document.querySelector("#detail").open&&document.querySelector("#detail-body").innerText.includes("21/100")&&document.querySelector("#detail-body").innerText.includes("历史共享场景")'),'details retain earlier protocol-specific evidence');
 await run('document.querySelector("#detail").close()');
 await run('document.querySelector(\'[data-edit="3-v13-mem0@30000"]\').click()');
 assert(await run('document.querySelector("#editor").open&&document.querySelector(\'[name="path"]\').disabled'),'editing freezes existing weight identity');
 await run('document.querySelector("#editor").close()');
 await go('task/5');assert(await run('document.querySelectorAll(".version-tabs a").length===2'),'five-task fixed and pos1cm split');assert(await run('document.body.innerText.includes("五任务评测状态待确认")'),'five-task TTC remains unconfirmed without inventing completed results');
 await go('task/7');assert(await run('document.querySelectorAll(".version-tabs a").length===1'),'seven-task separate version');
 await go('task/10');assert(await run('document.querySelectorAll("#main tbody tr").length===2&&document.body.innerText.includes("待评测")'),'ten-task distinct pending checkpoint rows');
 await run('document.querySelector("#add").click()');
 await run('document.querySelector(\'[name="method"]\').value="Mem-0";document.querySelector(\'[name="step"]\').value="40000";document.querySelector(\'[name="path"]\').value="/weights/new40k.pt";document.querySelector(\'[name="owner"]\').value="Test trainer";window.open=(url)=>{window.savedIssueURL=String(url)};document.querySelector("#edit-form").requestSubmit()');
 assert(await run('new URL(window.savedIssueURL).hostname==="github.com"&&new URL(window.savedIssueURL).searchParams.get("body").includes("/weights/new40k.pt")'),'web form prepares shared GitHub record with no in-browser token');
 await run('document.querySelector("#editor").close()');
 await go('updates');assert(await run('document.body.innerText.includes("Submit new issue")'),'shared confirmation and collaborator rules explained');
 for(let i=0;i<250;i++){if(await run('!document.querySelector("#sync").disabled'))break;await sleep(100);}
 // Inject hostile shared JSON through the actual sync/render path; never save to production.
 await run(`window.originalFetch=window.fetch;window.fetch=async()=>({ok:true,json:async()=>[{number:999,body:HandoffModel.issueBody({schema:2,kind:'checkpoint',target:'',task:'3',dataset:'3-latest',version:'latest',data_path:'/data',camera:'chest',method:'<img src=x onerror=window.xss=1>',step:40000,path:'/weights/40k.pt',doc:'',owner:'Trainer',run:'',protocol:'',note:'<script>window.xss=1</script>',h4:'',h8:'',h4unknown:0,h8unknown:0,state:'untested'}),updated_at:'2026-10-31T10:00:00Z',user:{login:'trainer'},author_association:'COLLABORATOR',labels:[]}]});document.querySelector('#sync').click()`);
 await sleep(200);await go('task/3/3-latest');
 assert(await run('document.querySelector(\'[data-row="issue-999"]\').textContent.includes("<img")&&!document.querySelector(\'[data-row="issue-999"] img\')&&!window.xss'),'hostile issue strings display as text, never HTML');
 await run('window.fetch=window.originalFetch');
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await sleep(200);
 assert(await run('document.documentElement.scrollWidth<=innerWidth'),'mobile page does not overflow');
 fs.writeFileSync(path.join(Q,'mobile.png'),Buffer.from((await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 assert(errors.length===0,'no uncaught page exceptions');
 const result={passed:true,checks,errors,at:new Date().toISOString()};fs.writeFileSync(path.join(Q,'BROWSER_QA.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{if(ws)ws.close();browser.kill('SIGTERM');}
