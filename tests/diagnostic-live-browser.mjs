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
 const target=await(await fetch('http://127.0.0.1:'+port+'/json/new?https://asimfish.github.io/psibot-dashboard/ours_threshold_sweep/sr_retest/#diagnostic-media',{method:'PUT'})).json();
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});});
 let id=0;const pending=new Map(),exceptions=[];
 ws.addEventListener('message',e=>{const x=JSON.parse(e.data);if(x.id){const p=pending.get(x.id);if(p){pending.delete(x.id);x.error?p.reject(Error(JSON.stringify(x.error))):p.resolve(x.result);}}else if(x.method==='Runtime.exceptionThrown')exceptions.push(x.params.exceptionDetails.text);});
 const cmd=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});
 const run=async expression=>{const r=await cmd('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await cmd('Runtime.enable');await cmd('Page.enable');
 for(let n=0;n<600;n++){if(await run('!!window.SafeLabV1&&!!document.querySelector("#v1Sources")'))break;await pause(100);}
 const evidence=await run(`(async()=>{
 const wait=async(fn,label)=>{for(let n=0;n<600;n++){if(fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('Timeout '+label);};
 const check=(yes,label)=>{if(!yes)throw Error(label);};
 await wait(()=>document.querySelector('#diagCase')?.options[0]?.value,'diagnostic cases');
 const q=id=>document.getElementById(id),formal=()=>['v1Results','v1Progress','v1Coverage'].map(id=>q(id).textContent).join('|');const before=formal();
 const all=[...q('diagCase').options].map(o=>({value:o.value,text:o.textContent}));check(all.length>=24,'24 diagnostic cases selectable');
 check(q('diagnostic-media').textContent.includes('不是正式成绩'),'diagnostic warning');
 q('diagOutcome').value='success';q('diagOutcome').dispatchEvent(new Event('change'));const success_count=q('diagCase').options.length;check(success_count===1&&q('diagCase').value,'published success filter');
 await wait(()=>q('diagStatus').textContent.includes('SHA通过'),'selected success log SHA');
 const selected=q('diagCase').value,metadata=q('diagMeta').textContent,log_status=q('diagStatus').textContent;check(metadata.includes('stage=diagnostic')&&metadata.includes('strict-v1'),'source remains diagnostic strict');
 const vs=[...document.querySelectorAll('#diagPlayers video')];check(vs.length===3,'three actual UI views');await wait(()=>vs.every(v=>Number.isFinite(v.duration)&&v.readyState>=2),'three real video metadata');
 q('diagPlay').click();await wait(()=>vs.every(v=>!v.paused&&v.currentTime>.2),'UI simultaneous playback');await new Promise(r=>setTimeout(r,1100));const played=vs.map(v=>v.currentTime);q('diagPlay').click();check(vs.every(v=>v.paused),'UI pause');
 q('diagSeek').value='3';q('diagSeek').dispatchEvent(new Event('input'));await wait(()=>vs.every(v=>!v.seeking&&Math.abs(v.currentTime-3)<.1),'UI simultaneous seek');
 const videos=vs.map(v=>({src:v.currentSrc,duration:v.duration,seek:v.currentTime,crossorigin:v.getAttribute('crossorigin'),sha_verified:false}));check(videos.every(v=>v.crossorigin===null),'no video CORS mode');
 const timeline_canvases=[...document.querySelectorAll('#diagPlayers canvas')].filter(c=>!c.hidden).length;check(timeline_canvases===3,'three real timelines');const details=[...document.querySelectorAll('#diagPlayers .tri-metrics')].map(x=>x.textContent);check(details.every(t=>t.includes('分数 未发布')&&t.includes('阳性 未发布')),'null scores and counters remain missing');
 q('diagOutcome').value='fail';q('diagSide').value='right';q('diagSide').dispatchEvent(new Event('change'));const right_fail_count=q('diagCase').options.length;check(right_fail_count===12,'right fail filter');
 q('diagOutcome').value='success';q('diagOutcome').dispatchEvent(new Event('change'));const unsupported_no_substitute=q('diagCase').value===''&&vs.every(v=>!v.getAttribute('src'));check(unsupported_no_substitute,'right success is missing, not substituted');
 q('diagTask').value='10';q('diagTask').dispatchEvent(new Event('change'));const missing_task_no_substitute=q('diagCase').value==='';check(missing_task_no_substitute,'unpublished task stays missing');check(formal()===before,'formal A/B text unchanged');
 return {url:location.href,origin:location.origin,selected_case:selected,all_selectable:all.length,success_count,right_fail_count,metadata,log_status,played,videos,timeline_canvases,null_details:details,unsupported_no_substitute,missing_task_no_substitute,formal_unchanged:true};})()`);
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 evidence.mobile_no_overflow=await run('document.documentElement.scrollWidth<=innerWidth');
 evidence.exceptions=exceptions;fs.writeFileSync(root+'diagnostic-live-browser.json',JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));if(exceptions.length||!evidence.mobile_no_overflow)throw Error('Browser errors or mobile overflow');
} catch(e){fs.writeFileSync(root+'diagnostic-live-browser-error.json',JSON.stringify({error:String(e),stderr:stderr.slice(-1600)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
