import {spawn} from 'node:child_process';
import fs from 'node:fs';
const root=(process.env.SAFELAB_MEDIA_QA_DIR||'/tmp/safelab-diagnostic-live')+'/';fs.mkdirSync(root,{recursive:true});
const browser=spawn('/usr/bin/google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--remote-allow-origins=*','--remote-debugging-port=0','--user-data-dir=/dev/shm/safelab_media_live_'+process.pid,'about:blank'],{stdio:['ignore','ignore','pipe']});
let stderr='',ws;browser.stderr.on('data',b=>stderr+=b);
const pause=ms=>new Promise(r=>setTimeout(r,ms));
try{
 let endpoint;for(let n=0;n<600;n++){endpoint=stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/)?.[1];if(endpoint)break;await pause(100);}
 if(!endpoint)throw Error('Chrome startup unavailable '+stderr.slice(-900));
 const port=new URL(endpoint).port;
 const target=await(await fetch('http://127.0.0.1:'+port+'/json/new?https://asimfish.github.io/safelab-handoff/',{method:'PUT'})).json();
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});});
 let id=0;const pending=new Map(),exceptions=[];
 ws.addEventListener('message',e=>{const x=JSON.parse(e.data);if(x.id){const p=pending.get(x.id);if(p){pending.delete(x.id);x.error?p.reject(Error(JSON.stringify(x.error))):p.resolve(x.result);}}else if(x.method==='Runtime.exceptionThrown')exceptions.push(x.params.exceptionDetails.text);});
 const cmd=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});
 const run=async expression=>{const r=await cmd('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await cmd('Runtime.enable');await cmd('Page.enable');await cmd('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});await cmd('Page.navigate',{url:'https://asimfish.github.io/safelab-handoff/'});
 for(let n=0;n<600;n++){if(await run('!!document.querySelector("#oracle-comparison")'))break;await pause(100);}
 const evidence=await run(`(async()=>{const wait=async(fn)=>{for(let i=0;i<600;i++){if(fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('online FD UI missing');};await wait(()=>document.querySelector('#oracle-comparison tbody tr'));const section=document.querySelector('#oracle-comparison'),heads=[...section.querySelectorAll('thead th')].map(x=>x.textContent),rows=section.querySelectorAll('tbody tr').length; if(heads.length!==4||!heads[2].includes('strict-fdvel-v1')||!heads[3].includes('placement-v1.1'))throw Error('three columns');if(section.textContent.includes('NaN%')||section.textContent.includes('Infinity%'))throw Error('fabricated numeric missing');const docs=await (await fetch('eval-v1.1.html')).text();if(!docs.includes('atan2')||!docs.includes('前向差分'))throw Error('FD definition missing');section.scrollIntoView();return {url:location.href,heads,rows,default_selector:document.querySelector('#metric-view').value,missing_columns_unpublished:section.textContent.includes('未发布'),fd_definition_published:true};})()`);
 evidence.exceptions=exceptions;fs.writeFileSync(root+'fd-live.json',JSON.stringify(evidence,null,2));if(exceptions.length)throw Error('JS exceptions');const shot=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'fd-live.jpg',Buffer.from(shot.data,'base64'));console.log(JSON.stringify(evidence));
} catch(e){fs.writeFileSync(root+'fd-error.json',JSON.stringify({error:String(e),stderr:stderr.slice(-1200)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
