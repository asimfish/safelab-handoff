import {spawn} from 'node:child_process';
import fs from 'node:fs';
const root=(process.env.SAFELAB_MEDIA_QA_DIR||'/tmp/safelab-live-media')+'/';fs.mkdirSync(root,{recursive:true});
const browser=spawn('/usr/bin/google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--remote-allow-origins=*','--remote-debugging-port=0','--user-data-dir=/dev/shm/safelab_media_live_'+process.pid,'about:blank'],{stdio:['ignore','ignore','pipe']});
let stderr='',ws;browser.stderr.on('data',b=>stderr+=b);
const pause=ms=>new Promise(r=>setTimeout(r,ms));
try{
 let endpoint;for(let n=0;n<600;n++){endpoint=stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/)?.[1];if(endpoint)break;await pause(100);}
 if(!endpoint)throw Error('Chrome startup unavailable '+stderr.slice(-900));
 const port=new URL(endpoint).port;
 const target=await(await fetch('http://127.0.0.1:'+port+'/json/new?https://asimfish.github.io/psibot-dashboard/ours_threshold_sweep/sr_retest/',{method:'PUT'})).json();
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});});
 let id=0;const pending=new Map(),exceptions=[];
 ws.addEventListener('message',e=>{const x=JSON.parse(e.data);if(x.id){const p=pending.get(x.id);if(p){pending.delete(x.id);x.error?p.reject(Error(JSON.stringify(x.error))):p.resolve(x.result);}}else if(x.method==='Runtime.exceptionThrown')exceptions.push(x.params.exceptionDetails.text);});
 const cmd=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});
 const run=async expression=>{const r=await cmd('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await cmd('Runtime.enable');await cmd('Page.enable');
 for(let n=0;n<600;n++){if(await run('!!window.SafeLabV1&&!!document.querySelector("#v1Sources")'))break;await pause(100);}
 const evidence=await run(`(async()=>{
 const base='https://asimfish.github.io/safelab-handoff/';
 const sha=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(n=>n.toString(16).padStart(2,'0')).join('');
 const fetchBytes=async u=>{const r=await fetch(u,{cache:'no-store',redirect:'error',credentials:'omit',signal:AbortSignal.timeout(25000)});if(!r.ok)throw Error('HTTP '+r.status+' '+u);return new Uint8Array(await r.arrayBuffer());};
 const index=JSON.parse(new TextDecoder().decode(await fetchBytes(base+'media/index.json'))),ms=index.manifests[0],mb=await fetchBytes(ms.url);if(await sha(mb)!==ms.sha256)throw Error('manifest SHA');
 const manifest=JSON.parse(new TextDecoder().decode(mb));let rows=0,events=0,bytes=0;const cases=[];
 for(const c of manifest.cases){const b=await fetchBytes(c.frame_log.url);if(b.length!==c.frame_log.bytes||await sha(b)!==c.frame_log.sha256)throw Error('frame identity '+c.case_id);const log=await SafeLabV1.decodeJSON(b,c.frame_log.url,2000000,c.frame_log);const valid=SafeLabV1.validateLog(log,c);rows+=valid.length;events+=valid.reduce((n,r)=>n+(r.physical_events?.length||0),0);bytes+=b.length;cases.push(c.case_id);}
 const video_checks=[];
 for(const [view,asset] of Object.entries(manifest.cases[0].videos)){
  const video=document.createElement('video');video.muted=true;video.preload='auto';video.playsInline=true;document.body.append(video);
  try{await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('metadata timeout')),12000);video.onloadedmetadata=()=>{clearTimeout(timer);resolve();};video.onerror=()=>{clearTimeout(timer);reject(Error('video '+video.error?.code));};video.src=asset.url;});
   const duration=video.duration;await video.play();await new Promise(r=>setTimeout(r,400));video.pause();const played=video.currentTime;const target=Math.min(2,duration/2);await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('seek timeout')),8000);video.onseeked=()=>{clearTimeout(timer);resolve();};video.currentTime=target;});video_checks.push({view,duration,played,seek:video.currentTime,target,sha_verified:false,crossorigin:video.getAttribute('crossorigin')});
  }catch(e){video_checks.push({view,error:String(e),sha_verified:false});}finally{video.pause();video.removeAttribute('src');video.load();video.remove();}
 }
 return {video_checks,origin:location.origin,manifest_sha_verified:true,logs:cases.length,bytes,rows,events,all_diagnostic:manifest.cases.every(c=>c.stage==='diagnostic'&&c.oracle_version==='strict-v1'),sources:document.querySelector('#v1Sources').textContent,scene_options:[...document.querySelector('#v1Scene').options].map(o=>({value:o.value,text:o.textContent})),log_states:[...document.querySelectorAll('.tri-log-state')].map(e=>e.textContent),cases};})()`);
 evidence.exceptions=exceptions;evidence.asset_validation_passed=evidence.logs===24&&evidence.rows===16161&&evidence.events===22;evidence.diagnostic_ui_available=evidence.scene_options.some(o=>o.value);if(!evidence.asset_validation_passed)throw Error('Live log totals differ');fs.writeFileSync(root+'pr48-live-browser.json',JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));
} catch(e){fs.writeFileSync(root+'pr48-live-browser-error.json',JSON.stringify({error:String(e),stderr:stderr.slice(-1600)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
