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
 const target=await(await fetch('http://127.0.0.1:'+port+'/json/new?https://asimfish.github.io/psibot-dashboard/ours_threshold_sweep/sr_retest/#v1Players',{method:'PUT'})).json();
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});});
 let id=0;const pending=new Map(),exceptions=[];
 ws.addEventListener('message',e=>{const x=JSON.parse(e.data);if(x.id){const p=pending.get(x.id);if(p){pending.delete(x.id);x.error?p.reject(Error(JSON.stringify(x.error))):p.resolve(x.result);}}else if(x.method==='Runtime.exceptionThrown')exceptions.push(x.params.exceptionDetails.text);});
 const cmd=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});
 const run=async expression=>{const r=await cmd('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await cmd('Runtime.enable');await cmd('Page.enable');await cmd('Page.navigate',{url:'https://asimfish.github.io/psibot-dashboard/ours_threshold_sweep/sr_retest/#v1Players'});
 for(let n=0;n<600;n++){if(await run('!!window.SafeLabV1&&!!document.querySelector("#v1Sources")'))break;await pause(100);}
 const evidence=await run(`(async()=>{
 const q=id=>document.getElementById(id),pause=ms=>new Promise(r=>setTimeout(r,ms));
 const wait=async(fn,label)=>{for(let n=0;n<600;n++){if(fn())return;await pause(100);}throw Error('Timeout '+label);};
 const check=(x,label)=>{if(!x)throw Error(label);},change=(id,value)=>{q(id).value=value;q(id).dispatchEvent(new Event('change'));};
 await wait(()=>q('v1Sources')?.textContent.includes('task10-strict-A-20261103'),'published task10 manifest');
 change('v1Task','10');change('v1Judgment','strict-v1');change('v1Stage','A');change('v1Condition','original-v1');
 await wait(()=>[...q('v1Scene').options].some(o=>o.textContent.includes('task10-scene001')),'shared scene001');
 const option=[...q('v1Scene').options].find(o=>o.textContent.includes('task10-scene001'));change('v1Scene',option.value);
 const cards=[...q('v1Players').querySelectorAll('.player-card')];check(cards.length===3,'three formal method columns');
 const choose=(n,token)=>{const sel=cards[n].querySelector('select');const op=[...sel.options].find(o=>o.value.includes(token));check(op,'published option '+token);sel.value=op.value;sel.dispatchEvent(new Event('change'));};
 choose(0,'mem0_original_off_30k_h4');choose(1,'ours_aligned_off_30k_h4');
 await wait(()=>cards.slice(0,2).every(c=>c.querySelector('.tri-log-state').textContent.includes('SHA通过')),'formal logs SHA');
 const stable=()=>['v1Results','v1Progress'].map(id=>q(id).textContent).join('|')+'|'+JSON.stringify([...q('v1Coverage').rows].map(r=>[...r.cells].slice(0,4).map(c=>c.textContent))),before=stable();
 const videos=cards.map(c=>c.querySelector('video'));check(!videos[2].getAttribute('src')&&cards[2].querySelector('.tri-log-state').textContent.includes('未发布'),'missing pi05 stays unpublished');
 const checks=[];
 for(const view of ['third_person','chest']){
  change('v1View',view);await wait(()=>cards.slice(0,2).every(c=>c.querySelector('.tri-log-state').textContent.includes('SHA通过')),'logs '+view);
  await wait(()=>videos.slice(0,2).every(v=>Number.isFinite(v.duration)&&v.readyState>=2),'metadata '+view);
  q('v1Play').click();await wait(()=>videos.slice(0,2).every(v=>!v.paused&&v.currentTime>.2),'formal shared playback '+view);await pause(700);const played=videos.slice(0,2).map(v=>v.currentTime);q('v1Play').click();check(videos.slice(0,2).every(v=>v.paused),'pause '+view);
  q('v1Seek').value='3';q('v1Seek').dispatchEvent(new Event('input'));await wait(()=>videos.slice(0,2).every(v=>!v.seeking&&Math.abs(v.currentTime-3)<.1),'seek '+view);
  checks.push({view,played,videos:videos.slice(0,2).map(v=>({src:v.currentSrc,duration:v.duration,seek:v.currentTime,crossorigin:v.getAttribute('crossorigin'),sha_verified:false})),logs:cards.slice(0,2).map(c=>c.querySelector('.tri-log-state').textContent)});
 }
 choose(0,'mem0_weak_off_30k_h4');await wait(()=>cards[0].querySelector('.tri-log-state').textContent.includes('SHA通过')&&videos[0].readyState>=2,'weak mem0 media');
 await videos[0].play();await wait(()=>videos[0].currentTime>.2,'weak video playback');videos[0].pause();const weak={selected:cards[0].querySelector('select').value,src:videos[0].currentSrc,time:videos[0].currentTime};
 const base='https://asimfish.github.io/safelab-handoff/';const bytes=async u=>{const r=await fetch(u,{cache:'no-store',redirect:'error',credentials:'omit',signal:AbortSignal.timeout(25000)});check(r.ok,'HTTP '+r.status);return new Uint8Array(await r.arrayBuffer());};
 const sha=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(n=>n.toString(16).padStart(2,'0')).join('');
 const board=JSON.parse(new TextDecoder().decode(await bytes(base+'data.json')));const pending=board.evaluations.filter(e=>e.id.startsWith('task10-eval-v11-20261103'));check(pending.length===16&&pending.every(e=>e.success===null&&e.oracle_version==='placement-v1.1'&&e.admission.executor_parity.passed===false),'published placement rows remain pending');
 const index=JSON.parse(new TextDecoder().decode(await bytes(base+'media/index.json'))),entry=index.manifests.find(m=>m.url.includes('/10/')),raw=await bytes(entry.url);check(await sha(raw)===entry.sha256,'manifest SHA');const manifest=JSON.parse(new TextDecoder().decode(raw));check(manifest.cases.length===48,'48 task10 cases');
 let rows=0,events=0;
 for(const c of manifest.cases){check(c.stage==='A'&&c.protocol_version==='SafeLab-Eval-v1'&&c.oracle_version==='strict-v1','strict A preserved');const b=await bytes(c.frame_log.url);check(b.length===c.frame_log.bytes&&await sha(b)===c.frame_log.sha256,'log bytes SHA '+c.case_id);const log=await SafeLabV1.decodeJSON(b,c.frame_log.url,2000000,c.frame_log);const rs=SafeLabV1.validateLog(log,c);rows+=rs.length;events+=rs.reduce((s,r)=>s+(r.physical_events?.length||0),0);}
 const unchanged=stable()===before;check(unchanged,'media controls do not change formal scores');
 check(checks.every(c=>c.videos.every(v=>v.src.startsWith('https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/media-v1/10/')&&v.crossorigin===null)),'required migrated public URLs');
 return {url:location.href,stage:q('v1Stage').value,oracle:q('v1Judgment').value,scene:q('v1Scene').value,method_columns:3,playable_columns:2,unpublished_method:'pi0.5',pi05_status:cards[2].querySelector('.tri-log-state').textContent,checks,weak,placement_pending:pending.length,manifest_cases:manifest.cases.length,logs_verified:48,rows,events,formal_scores_unchanged:unchanged,sources:q('v1Sources').textContent};})()`);
 evidence.exceptions=exceptions;fs.writeFileSync(root+'task10-live-browser.json',JSON.stringify(evidence,null,2));if(exceptions.length)throw Error('browser JS exceptions '+JSON.stringify(exceptions));
 await run('document.querySelector("#v1Players").scrollIntoView()');const desktop=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task10-formal-desktop.jpg',Buffer.from(desktop.data,'base64'));
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await pause(400);evidence.mobile={width:390,overflow:await run('document.documentElement.scrollWidth>innerWidth')};
 const mobile=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task10-formal-mobile.jpg',Buffer.from(mobile.data,'base64'));fs.writeFileSync(root+'task10-live-browser.json',JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));
} catch(e){fs.writeFileSync(root+'task10-live-browser-error.json',JSON.stringify({error:String(e),stderr:stderr.slice(-1600)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
