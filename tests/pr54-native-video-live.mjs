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
 const targets=[{"case_id": "mem0_30k__smoke20_h8_v180_o1234_r002", "url": "https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/media-v1/7/7-mem0/30000/original-v1/mem0_30k__smoke20_h8_v180_o1234_r002/chest.9c235fa369560497.mp4", "status": 206, "range": "bytes 0-1023/1555036", "mp4_signature": true}, {"case_id": "mem0_30k__smoke20_h8_v180_o4321_r006", "url": "https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/media-v1/7/7-mem0/30000/original-v1/mem0_30k__smoke20_h8_v180_o4321_r006/chest.9841bfb1a9a7ef03.mp4", "status": 206, "range": "bytes 0-1023/1560573", "mp4_signature": true}];
 const results=[];
 for(const item of targets){const e=await run(`(async()=>{const item=${JSON.stringify(item)},v=document.createElement('video');v.muted=true;v.preload='auto';v.src=item.url;document.body.append(v);const wait=async(fn)=>{for(let n=0;n<600;n++){if(fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('video timeout '+item.case_id);};await wait(()=>v.readyState>=3&&v.duration>0);await v.play();await wait(()=>!v.paused&&v.currentTime>.5);v.pause();v.currentTime=Math.min(10,v.duration/2);await wait(()=>!v.seeking&&v.readyState>=2);const result={case_id:item.case_id,url:v.currentSrc,duration:v.duration,played:true,seek:v.currentTime,width:v.videoWidth,height:v.videoHeight,crossorigin:v.getAttribute('crossorigin')};v.remove();return result;})()`);results.push(e);}
 fs.writeFileSync(root+'pr54-videos.json',JSON.stringify({scope:'native Chrome playback of two actual public video URLs only; no formal score or unpublished page validation',results,exceptions},null,2));if(exceptions.length)throw Error('JS exceptions');console.log(JSON.stringify(results));
} catch(e){fs.writeFileSync(root+'error.json',JSON.stringify({error:String(e)}));console.error(e);process.exitCode=1;}finally{if(ws)ws.close();browser.kill('SIGTERM');}
