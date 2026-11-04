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
 await cmd('Runtime.enable');await cmd('Page.enable');await cmd('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});await cmd('Page.navigate',{url:'https://asimfish.github.io/psibot-dashboard/ours_threshold_sweep/sr_retest/#diagnostic-media'});
 for(let n=0;n<600;n++){if(await run('!!window.SafeLabV1&&!!document.querySelector("#v1Sources")'))break;await pause(100);}
 const evidence=await run(`(async()=>{
 const q=id=>document.getElementById(id),pause=ms=>new Promise(r=>setTimeout(r,ms)),check=(v,label)=>{if(!v)throw Error(label);},change=(id,val)=>{q(id).value=val;q(id).dispatchEvent(new Event('change'));};
 const wait=async(fn,label)=>{for(let n=0;n<600;n++){if(fn())return;await pause(100);}throw Error('Timeout '+label);};
 await wait(()=>q('v1Sources')?.textContent.includes('t1035-mem0-trainresize-strict-diagnostic-20261103'),'new Mem0 manifest');
 change('diagTask','3');change('diagConfig','all');change('diagSide','all');change('diagOutcome','all');
 const options=[...q('diagCase').options].map(o=>({value:o.value,text:o.textContent}));check(options.length===64,'64 diagnostic cases');check(options.filter(o=>o.value.startsWith('t1035_mem0_trainresize_r6')).length===16,'16 new cases selectable');
 const formal=()=>['v1Results','v1Progress'].map(id=>q(id).textContent).join('|')+'|'+JSON.stringify([...q('v1Coverage').rows].map(r=>[...r.cells].slice(0,4).map(c=>c.textContent))),before=formal();
 const bytes=async u=>{const r=await fetch(u,{cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(25000)});check(r.ok,'HTTP '+r.status);return new Uint8Array(await r.arrayBuffer());},sha=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(n=>n.toString(16).padStart(2,'0')).join('');
 const base='https://asimfish.github.io/safelab-handoff/',index=JSON.parse(new TextDecoder().decode(await bytes(base+'media/index.json'))),board=JSON.parse(new TextDecoder().decode(await bytes(base+'data.json'))),load=async token=>{const e=index.manifests.find(e=>e.url.includes(token));check(e,'indexed '+token);const raw=await bytes(e.url);check(await sha(raw)===e.sha256,'manifest SHA '+token);return {entry:e,manifest:JSON.parse(new TextDecoder().decode(raw))};};
 const mem=await load('t1035-mem0-trainresize'),ttc=await load('t1035-round7-strict-diagnostic');check(mem.entry.sha256==='6dca8bae8cf373ddad5cf4c2df2f2bc87fe7726c9063d2ed61a4097b28602648','expected manifest SHA');
 const ids=SafeLabV1.identities(board),key=c=>{const id=ids.find(r=>r.id===c.record&&r.step===c.checkpoint);return JSON.stringify([c.protocol_version,c.oracle_version,c.task,c.stage,c.condition_version,c.scene_list_hash.replace(/^sha256:/,''),c.scene_id,c.side,c.seed,id?.dataset,id?.camera,c.render_config_hash.replace(/^sha256:/,''),c.horizon]);};
 const pairs=mem.manifest.cases.flatMap(c=>{const t=ttc.manifest.cases.find(t=>t.record==='3-v13-ours'&&key(t)===key(c));return t?[{horizon:c.horizon,scene:c.scene_id,mem0:c,ttc:t}]:[];});check(pairs.filter(p=>p.horizon===4).length===5&&pairs.filter(p=>p.horizon===8).length===6,'exact matched pair counts');
 let rows=0,events=0,switches=0;
 for(const c of mem.manifest.cases){check(SafeLabV1.validateCase(c,board).length===0&&c.stage==='diagnostic'&&c.oracle_version==='strict-v1','case source binding');const e=board.evaluations.find(e=>e.id===c.evaluation_id),source=board.evaluations.find(x=>x.id===e?.source_evaluation_id);check(e.derived_not_additional_trials===true&&e.success===null&&e.formal_score_eligible===false&&e.source_condition_version===source.condition_version&&c.condition_version==='original-v1','alias preserves source, no duplicate trial score');const b=await bytes(c.frame_log.url);check(b.length===c.frame_log.bytes&&await sha(b)===c.frame_log.sha256,'log bytes SHA');const log=await SafeLabV1.decodeJSON(b,c.frame_log.url,2000000,c.frame_log),rs=SafeLabV1.validateLog(log,c);check(!log.sampling,'no downsample');rows+=rs.length;events+=rs.reduce((n,r)=>n+(r.physical_events?.length||0),0);switches+=rs.filter(r=>r.switched===true).length;}
 check(rows===13591&&events===36&&switches===47,'new log totals');
 const vs=[...q('diagPlayers').querySelectorAll('video')];check(vs.length===3,'single-case three-camera diagnostic UI');const playback=[];
 for(const horizon of [4,8]){
  const pair=pairs.find(p=>p.horizon===horizon&&p.scene==='v13-right-s262200101');check(pair,'shared representative scene');const selected=[];
  for(const method of ['ttc','mem0']){
   const c=pair[method];change('diagCase',c.case_id);await wait(()=>q('diagMeta').textContent.includes(c.evaluation_id)&&q('diagStatus').textContent.includes('SHA通过'),'selected '+method+' log');check(q('diagMeta').textContent.includes('stage=diagnostic')&&q('diagMeta').textContent.includes('strict-v1'),'diagnostic label');
   await wait(()=>vs.every(v=>Number.isFinite(v.duration)&&v.readyState>=2),'metadata '+method);q('diagPlay').click();await wait(()=>vs.every(v=>!v.paused&&v.currentTime>.2),'play '+method);await pause(400);const played=vs.map(v=>v.currentTime);q('diagPlay').click();check(vs.every(v=>v.paused),'pause');
   q('diagSeek').value='3';q('diagSeek').dispatchEvent(new Event('input'));await wait(()=>vs.every(v=>!v.seeking&&Math.abs(v.currentTime-3)<.1),'seek3');
   const videos=vs.map(v=>({url:v.currentSrc,duration:v.duration,seek:v.currentTime,crossorigin:v.getAttribute('crossorigin'),sha_verified:false}));check(videos.every(v=>v.url.includes('/'+c.case_id+'/')&&v.url.startsWith('https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/media-v1/3/')&&v.crossorigin===null),'correct immutable case URL');selected.push({method,case_id:c.case_id,metadata:q('diagMeta').textContent,played,videos,log:q('diagStatus').textContent});
  }
  playback.push({horizon,scene:pair.scene,exact_key:key(pair.mem0),mode:'sequential same-scene comparison in actual UI; not simultaneous two-method playback',selected});
 }
 check(SafeLabV1.pairedScenes([...mem.manifest.cases,...ttc.manifest.cases],board).length===0,'diagnostic not formal scene groups');check(formal()===before,'formal scores unchanged');
 return {url:location.href,total_diagnostic_cases:64,new_cases:16,exact_pairs:{h4:5,h8:6},logs_verified:16,rows,events,switches,playback,simultaneous_method_pair_UI:false,ui_mode:'single case, three camera views',formal_unchanged:true,manifest_sha:mem.entry.sha256,source_condition_preserved:true};})()`);
 evidence.exceptions=exceptions;fs.writeFileSync(root+'task3-matched-diagnostic-live.json',JSON.stringify(evidence,null,2));if(exceptions.length)throw Error('JS exceptions');
 await run('document.querySelector("#diagPlayers").scrollIntoView()');const desktop=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task3-matched-desktop.jpg',Buffer.from(desktop.data,'base64'));
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await pause(400);evidence.mobile_no_overflow=await run('document.documentElement.scrollWidth<=innerWidth');const mobile=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task3-matched-mobile.jpg',Buffer.from(mobile.data,'base64'));fs.writeFileSync(root+'task3-matched-diagnostic-live.json',JSON.stringify(evidence,null,2));if(!evidence.mobile_no_overflow)throw Error('mobile overflow');console.log(JSON.stringify(evidence));
} catch(e){fs.writeFileSync(root+'task3-matched-diagnostic-live-error.json',JSON.stringify({error:String(e),stderr:stderr.slice(-1600)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
