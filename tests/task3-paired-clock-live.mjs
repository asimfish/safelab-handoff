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
 const q=id=>document.getElementById(id),pause=ms=>new Promise(r=>setTimeout(r,ms)),check=(v,label)=>{if(!v)throw Error(label);},change=(id,val)=>{q(id).value=val;q(id).dispatchEvent(new Event('change'));},wait=async(fn,label)=>{for(let n=0;n<600;n++){if(fn())return;await pause(100);}throw Error('Timeout '+label);};
 await wait(()=>q('diagPairScene')?.options.length===11,'published PR568 paired UI and 11 exact pairs');check(q('diagMode').value==='paired','default diagnostic paired mode');
 const formal=()=>['v1Results','v1Progress'].map(id=>q(id).textContent).join('|')+'|'+JSON.stringify([...q('v1Coverage').rows].map(r=>[...r.cells].slice(0,4).map(c=>c.textContent))),before=formal();
 const results=[],vs=[...q('diagPairPlayers').querySelectorAll('video')];check(vs.length===2,'two actual method video elements');
 for(const h of ['4','8']){
  change('diagPairHorizon',h);check(q('diagPairScene').options.length===(h==='4'?5:6),'exact pair count h'+h);
  const choice=[...q('diagPairScene').options].find(o=>o.textContent.includes('v13-right-s262200101'));check(choice,'same representative scene');change('diagPairScene',choice.value);
  await wait(()=>[...q('diagPairPlayers').querySelectorAll('.tri-log-state')].every(e=>e.textContent.includes('日志SHA / 解析通过')),'both verified logs');
  if(h==='8'){const selects=[...q('diagPairPlayers').querySelectorAll('select')];for(const [i,view]of [[1,'head'],[3,'chest']]){selects[i].value=view;selects[i].dispatchEvent(new Event('change'));}await wait(()=>[...q('diagPairPlayers').querySelectorAll('.tri-log-state')].every(e=>e.textContent.includes('日志SHA / 解析通过')),'independent head/chest logs');}
  await wait(()=>vs.every(v=>v.readyState>=3&&v.duration>0),'video metadata and buffered start');q('diagPairPlay').click();await wait(()=>vs.every(v=>!v.paused&&!v.seeking&&v.currentTime>.1),'actual simultaneous playback');
  const initial=vs.map(v=>v.currentTime),samples=[],start=performance.now();let excluded=0;
  await new Promise(resolve=>{function sample(){if(vs.every(v=>!v.paused&&!v.seeking&&v.readyState>=3))samples.push({a:vs[0].currentTime,b:vs[1].currentTime,error_s:Math.abs(vs[0].currentTime-vs[1].currentTime)});else excluded++;if(performance.now()-start>=2600)resolve();else requestAnimationFrame(sample);}requestAnimationFrame(sample);});
  const final=vs.map(v=>v.currentTime),max_error_s=Math.max(...samples.map(x=>x.error_s));check(samples.length>=30&&excluded===0,'continuous paired playback without excluded buffering frames');check(final.every((t,i)=>t-initial[i]>2),'both actual clocks advanced >2s');check(max_error_s<=1/15,'synchronization within one 15Hz frame');
  q('diagPairPlay').click();check(vs.every(v=>v.paused),'shared pause');const paused=vs.map(v=>v.currentTime);await pause(250);check(vs.every((v,i)=>Math.abs(v.currentTime-paused[i])<.001),'both stay paused');
  q('diagPairSeek').value='3';q('diagPairSeek').dispatchEvent(new Event('input'));await wait(()=>vs.every(v=>!v.seeking&&Math.abs(v.currentTime-3)<.01),'both seek3');const seek=vs.map(v=>v.currentTime);
  change('diagPairSpeed','2');check(vs.every(v=>v.playbackRate===2),'shared 2x');q('diagPairPlay').click();await wait(()=>vs.every(v=>!v.paused&&!v.seeking),'2x paired play');const fastStart=vs.map(v=>v.currentTime);await pause(700);const fastEnd=vs.map(v=>v.currentTime);check(fastEnd.every((t,i)=>t-fastStart[i]>1),'2x actual advancement');q('diagPairPlay').click();change('diagPairSpeed','1');
  const meta=[...q('diagPairPlayers').querySelectorAll('.source-stamp')].map(e=>e.textContent),logs=[...q('diagPairPlayers').querySelectorAll('.tri-log-state')].map(e=>e.textContent);
  check(meta.every(x=>x.includes('诊断，不是正式成绩')&&x.includes('placement-v1.1：未发布')),'diagnostic and unpublished other oracle');check(q('diagPairDifference').querySelectorAll('table tr').length===4,'three stage delta rows');check(vs.every(v=>v.currentSrc.startsWith('https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/media-v1/3/')&&!v.hasAttribute('crossorigin')),'new prefix direct video');check(formal()===before,'formal results and v1.1 coverage unchanged');
  results.push({horizon:+h,key:JSON.parse(choice.value),scene:choice.textContent,initial,final,samples:samples.length,excluded,max_error_s,seek,fastStart,fastEnd,meta,logs,difference:q('diagPairDifference').textContent,videos:vs.map(v=>({url:v.currentSrc,duration:v.duration}))});
 }
 change('diagPairTask','5');check(q('diagPairScene').options.length===1&&q('diagPairScene').options[0].value==='','unpublished task has no substitute pair');check(vs.every(v=>v.paused&&!v.getAttribute('src')),'unpublished pair clears both videos');change('diagPairTask','3');
 change('diagMode','single');await wait(()=>q('diagCase').options.length===64,'single mode64cases preserved');check(vs.every(v=>v.paused),'inactive paired videos paused');change('diagMode','paired');check([...q('diagPlayers').querySelectorAll('video')].every(v=>v.paused),'inactive single videos paused');
 check(formal()===before,'formal table remains unchanged after all controls');return {url:location.href,source_mode:'pure online published code, data, videos and same-origin logs; no interception or overlay',exact_pairs:{h4:5,h8:6},results,missing_pair_no_substitute:true,single_mode_cases:64,formal_unchanged:true};})()`);
 evidence.exceptions=exceptions;fs.writeFileSync(root+'task3-paired-clock-live.json',JSON.stringify(evidence,null,2));if(exceptions.length)throw Error('JS exceptions');
 await run('document.querySelector("#diagPairPlayers").scrollIntoView()');const desktop=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task3-matched-desktop.jpg',Buffer.from(desktop.data,'base64'));
 await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await pause(400);evidence.mobile_no_overflow=await run('document.documentElement.scrollWidth<=innerWidth');const mobile=await cmd('Page.captureScreenshot',{format:'jpeg',quality:75,captureBeyondViewport:false});fs.writeFileSync(root+'task3-matched-mobile.jpg',Buffer.from(mobile.data,'base64'));fs.writeFileSync(root+'task3-paired-clock-live.json',JSON.stringify(evidence,null,2));if(!evidence.mobile_no_overflow)throw Error('mobile overflow');console.log(JSON.stringify(evidence));
} catch(e){fs.writeFileSync(root+'task3-paired-clock-live-error.json',JSON.stringify({error:String(e),stderr:stderr.slice(-1600)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
