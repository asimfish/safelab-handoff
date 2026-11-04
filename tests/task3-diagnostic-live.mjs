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
 const q=id=>document.getElementById(id),pause=ms=>new Promise(r=>setTimeout(r,ms)),check=(v,label)=>{if(!v)throw Error(label);};
 const wait=async(fn,label)=>{for(let n=0;n<600;n++){if(fn())return;await pause(100);}throw Error('Timeout '+label);},change=(id,value)=>{q(id).value=value;q(id).dispatchEvent(new Event('change'));};
 await wait(()=>q('v1Sources')?.textContent.includes('t1035-round7-strict-diagnostic-20261103'),'published Task3 manifest');
 change('diagTask','3');change('diagConfig','all');change('diagSide','all');change('diagOutcome','all');
 const options=[...q('diagCase').options].map(o=>({value:o.value,text:o.textContent}));check(options.length===48,'48 diagnostic cases including retained pi05');check(options.filter(o=>o.value.startsWith('t1035_')).length===24,'24 new cases selectable');
 const formal=()=>['v1Results','v1Progress'].map(id=>q(id).textContent).join('|')+'|'+JSON.stringify([...q('v1Coverage').rows].map(r=>[...r.cells].slice(0,4).map(c=>c.textContent))),before=formal();
 const vs=[...q('diagPlayers').querySelectorAll('video')];check(vs.length===3,'three real diagnostic camera views');
 const selections=[
  't1035_trainresize_t1035_ours_r0_c30000_h4_right_s262200101',
  't1035_trainresize_t1035_ours_r0_c30000_h8_right_s262200101',
  't1035_D0_t1035_r0_v13_30k_h4_right_s262200101'];
 const checks=[];
 for(const cid of selections){
  change('diagCase',cid);await wait(()=>q('diagMeta').textContent.includes(cid.includes('_D0_')?'t1035-r3-diag-d0':cid.includes('_h8_')?'c30-h8':'c30-h4')&&q('diagStatus').textContent.includes('SHA通过'),'selected log '+cid);
  const meta=q('diagMeta').textContent;check(meta.includes('stage=diagnostic')&&meta.includes('strict-v1'),'strict diagnostic identity');
  await wait(()=>vs.every(v=>Number.isFinite(v.duration)&&v.readyState>=2),'three view metadata '+cid);q('diagPlay').click();await wait(()=>vs.every(v=>!v.paused&&v.currentTime>.2),'three view playback '+cid);await pause(500);const played=vs.map(v=>v.currentTime);q('diagPlay').click();check(vs.every(v=>v.paused),'shared pause');
  change('diagSeek','3');q('diagSeek').dispatchEvent(new Event('input'));await wait(()=>vs.every(v=>!v.seeking&&Math.abs(v.currentTime-3)<.1),'three view seek '+cid);
  const videos=vs.map(v=>({url:v.currentSrc,duration:v.duration,seek:v.currentTime,crossorigin:v.getAttribute('crossorigin'),sha_verified:false}));check(videos.every(v=>v.url.includes('/'+cid+'/')&&v.url.startsWith('https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/media-v1/3/')&&v.crossorigin===null),'correct case owned URLs');
  checks.push({case_id:cid,metadata:meta,log:q('diagStatus').textContent,played,videos,canvases:[...q('diagPlayers').querySelectorAll('canvas')].filter(c=>!c.hidden).length});
 }
 const bytes=async u=>{const r=await fetch(u,{cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(25000)});check(r.ok,'HTTP '+r.status);return new Uint8Array(await r.arrayBuffer());},sha=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(n=>n.toString(16).padStart(2,'0')).join('');
 const base='https://asimfish.github.io/safelab-handoff/',index=JSON.parse(new TextDecoder().decode(await bytes(base+'media/index.json'))),entry=index.manifests.find(m=>m.url.includes('t1035-round7')),raw=await bytes(entry.url);check(await sha(raw)===entry.sha256&&entry.sha256==='932d44890c6f3823e267927d69df873f4a80c14b00ce5637c7ceb5d63c45966d','published manifest identity');const manifest=JSON.parse(new TextDecoder().decode(raw)),board=JSON.parse(new TextDecoder().decode(await bytes(base+'data.json')));let rows=0,events=0,switches=0;
 for(const c of manifest.cases){check(SafeLabV1.validateCase(c,board).length===0,'live binding '+c.case_id);const b=await bytes(c.frame_log.url);check(b.length===c.frame_log.bytes&&await sha(b)===c.frame_log.sha256,'log identity '+c.case_id);const log=await SafeLabV1.decodeJSON(b,c.frame_log.url,2000000,c.frame_log);const rs=SafeLabV1.validateLog(log,c);check(!log.sampling,'full unsampled log');rows+=rs.length;events+=rs.reduce((n,r)=>n+(r.physical_events?.length||0),0);switches+=rs.filter(r=>r.switched===true).length;}
 check(rows===18271&&events===53&&switches===106,'all log totals');check(SafeLabV1.pairedScenes(manifest.cases).length===0,'diagnostic never formal pairing');
 const d0=manifest.cases.find(c=>c.case_id===selections[2]),ttc=manifest.cases.find(c=>c.case_id===selections[0]);check(d0.render_config_hash===ttc.render_config_hash&&d0.scene_id===ttc.scene_id&&d0.seed===ttc.seed,'same scene render diagnostic candidates');check(d0.condition_version!==ttc.condition_version&&d0.scene_list_hash!==ttc.scene_list_hash,'different comparison cohorts preserved');
 const config=[...q('diagConfig').options].find(o=>o.value.includes('t1035-r3-diag-d0'));check(config,'D0 config');change('diagConfig',config.value);change('diagSide','left');change('diagOutcome','success');check(q('diagCase').value===''&&vs.every(v=>!v.getAttribute('src')),'D0 left success unpublished, no substitution');
 change('diagSide','all');change('diagOutcome','all');change('diagConfig','all');change('diagCase',selections[2]);await wait(()=>q('diagStatus').textContent.includes('SHA通过'),'restore D0');
 check(formal()===before,'formal scores/progress/coverage unchanged by diagnostic controls');
 return {url:location.href,all_diagnostic_cases:48,new_cases:24,checks,manifest_sha256:entry.sha256,logs_verified:24,rows,events,switches,render_hash:d0.render_config_hash,automatic_cohort_pairing:false,cohort_differences:['condition_version','scene_list_hash'],formal_unchanged:true,D0_left_success_unpublished:true,sources:q('v1Sources').textContent};})()`);
 evidence.exceptions=exceptions;fs.writeFileSync(root+'task3-diagnostic-live.json',JSON.stringify(evidence,null,2));if(exceptions.length)throw Error('JS exceptions');
 await run('document.querySelector("#diagPlayers").scrollIntoView()');const desktop=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task3-diagnostic-desktop.jpg',Buffer.from(desktop.data,'base64'));
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await pause(400);evidence.mobile_no_overflow=await run('document.documentElement.scrollWidth<=innerWidth');const mobile=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task3-diagnostic-mobile.jpg',Buffer.from(mobile.data,'base64'));fs.writeFileSync(root+'task3-diagnostic-live.json',JSON.stringify(evidence,null,2));if(!evidence.mobile_no_overflow)throw Error('mobile overflow');console.log(JSON.stringify(evidence));
} catch(e){fs.writeFileSync(root+'task3-diagnostic-live-error.json',JSON.stringify({error:String(e),stderr:stderr.slice(-1600)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
