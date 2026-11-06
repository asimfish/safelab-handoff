'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib'),{execFileSync}=require('node:child_process');
const LIMITS={snapshot:50000000,asset:2000000,manifest:1000000,index:256000};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
// Exact bucket endpoints already used by reviewed media; no arbitrary external hosts.
const PUBLIC_MEDIA_ORIGINS=new Set(['https://zenith-a02012413.bj.bcebos.com','https://zenith-a02012413.tos-cn-beijing.volces.com']);
function publicMediaURL(value,task,alias){
 const u=new URL(value);
 if(!PUBLIC_MEDIA_ORIGINS.has(u.origin)||u.href!==value||u.username||u.password||u.search||u.hash||/%(?:2e|2f|5c)/i.test(u.pathname))throw Error('Public media must use a clean approved bucket URL');
 const producerTask5=alias==='task5'&&String(task)==='5'&&/^\/liyufeng\/safelab-public\/media-v1\/task5\/(?:[^/?#]+\/)*[^/?#]+\.mp4$/.test(u.pathname);if(producerTask5)return {legacy:true};const match=u.pathname.match(/^\/(liyufeng\/)?safelab-public\/media-v1\/(3|5|7|10)\/(?:[^/?#]+\/)*[^/?#]+\.mp4$/);
 if(!match||task!=null&&match[2]!==String(task))throw Error('Public media path must use liyufeng/safelab-public/media-v1/<task>/ (old prefix is migration-only)');
 return {legacy:!match[1]};
}
function localLogPath(url){
 const u=new URL(url);
 if(u.origin!=='https://asimfish.github.io'||u.username||u.password||u.search||u.hash||!u.pathname.startsWith('/safelab-handoff/media/frame_logs/'))throw Error('Frame log must use clean same-origin HTTPS URL');
 const name=decodeURIComponent(u.pathname.slice('/safelab-handoff/'.length));
 if(name.includes('\\')||path.posix.normalize(name)!==name||!/^media\/frame_logs\/(?:[A-Za-z0-9_.-]+\/)+[A-Za-z0-9_.-]+\.json(?:\.gz)?$/.test(name))throw Error('Invalid frame-log repository path');
 return name;
}
function readLog(root,name,limits=LIMITS){
 const file=path.join(root,name),stat=fs.lstatSync(file);
 if(!stat.isFile()||stat.isSymbolicLink()||stat.size>limits.asset)throw Error('Invalid/oversized frame log: '+name);
 const wire=fs.readFileSync(file),gzip=name.endsWith('.gz');
 if(wire.length>limits.asset)throw Error('Frame-log wire exceeds limit');
 const decoded=gzip?zlib.gunzipSync(wire,{maxOutputLength:limits.asset}):wire;
 if(decoded.length>limits.asset)throw Error('Decoded frame log exceeds limit');
 const log=JSON.parse(decoded.toString('utf8'));
 if(log.schema_version!=='safelab-frame-log-v1'||!Array.isArray(log.rows)||log.rows.length>60000)throw Error('Invalid frame-log envelope');
 let priorTime=-1,priorFrame=-1;
 for(const row of log.rows){
  if(!Number.isFinite(row.t_sim)||row.t_sim<0||!Number.isInteger(row.frame)||row.frame<0||row.t_sim<=priorTime||row.frame<=priorFrame)throw Error('Frame-log clocks must strictly increase');
  priorTime=row.t_sim;priorFrame=row.frame;
 }
 if(log.sampling&&(log.sampling.retained_rows!==log.rows.length||!Number.isInteger(log.sampling.original_rows)||log.sampling.original_rows<log.rows.length))throw Error('Sampling counts do not conserve rows');
 return {wire,decoded,log,gzip};
}
function validateAsset(asset,entry){
 if(!Number.isInteger(asset.bytes)||asset.bytes!==entry.wire.length||String(asset.sha256).replace(/^sha256:/,'')!==hash(entry.wire))throw Error('Frame-log wire bytes/SHA mismatch');
 if((asset.encoding||'identity')!==(entry.gzip?'gzip':'identity'))throw Error('Frame-log encoding mismatch');
 if(entry.gzip||asset.decoded_bytes!=null||asset.decoded_sha256!=null){
  if(asset.decoded_bytes!==entry.decoded.length||String(asset.decoded_sha256).replace(/^sha256:/,'')!==hash(entry.decoded))throw Error('Frame-log decoded bytes/SHA mismatch');
 }
}
function inspect(root,files,limits=LIMITS){
 const tracked=new Set(files),frames=new Map(),report={snapshot_bytes:0,media_bytes:0,frame_log_bytes:0,frame_logs:0,manifests:0,public_media_references:0,legacy_public_media_references:0};
 for(const name of files){
  const stat=fs.lstatSync(path.join(root,name));report.snapshot_bytes+=stat.size;
  if(name.startsWith('reports/')&&stat.size>200000)throw Error('Evidence over 200000 bytes must use TOS reports-v1: '+name);
  if(name.startsWith('media/')){if(stat.isSymbolicLink()||!stat.isFile())throw Error('Media must be regular tracked files');report.media_bytes+=stat.size;}
  if(name.startsWith('media/frame_logs/')&&!name.endsWith('/.gitkeep')){
   if(!/\.json(?:\.gz)?$/.test(name))throw Error('Only derived JSON frame logs allowed');
   const entry=readLog(root,name,limits);frames.set(name,entry);report.frame_log_bytes+=stat.size;report.frame_logs++;
  }
  if(name==='media/index.json'&&stat.size>limits.index)throw Error('Media index exceeds limit');
 }
 if(report.snapshot_bytes>limits.snapshot)throw Error('Tracked publication snapshot exceeds '+limits.snapshot+' byte budget');
 const used=new Set();
 for(const name of files.filter(n=>/^media\/manifests\/.+\.json$/.test(n))){
  if(fs.statSync(path.join(root,name)).size>limits.manifest)throw Error('Media manifest exceeds limit');
  const manifest=JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));if(!Array.isArray(manifest.cases))throw Error('Missing manifest cases');report.manifests++;
  for(const item of manifest.cases){
   for(const asset of Object.values(item.videos||{})){if(!asset)continue;const policy=publicMediaURL(asset.url,item.task,asset.publication_prefix_alias);report.public_media_references++;if(policy.legacy)report.legacy_public_media_references++;}
   if(!item.frame_log)continue;const target=localLogPath(item.frame_log.url);if(!tracked.has(target)||!frames.has(target))throw Error('Frame log is not a tracked local asset');const entry=frames.get(target);validateAsset(item.frame_log,entry);if(entry.log.case_id!==item.case_id)throw Error('Frame-log case binding mismatch');used.add(target);
   if(item.frame_log_previous){const previous=localLogPath(item.frame_log_previous.url);if(!tracked.has(previous)||!frames.has(previous))throw Error('Previous compatibility log must remain tracked');const old=frames.get(previous);validateAsset(item.frame_log_previous,old);if(!entry.gzip||old.gzip||old.log.case_id!==item.case_id||!entry.decoded.equals(old.decoded))throw Error('Compatibility log must be byte-identical plain predecessor of gzip');used.add(previous);}
  }
 }
 for(const name of frames.keys())if(!used.has(name))throw Error('Unreferenced frame log: '+name);
 return report;
}
if(require.main===module){try{const root=path.resolve(__dirname,'..'),files=execFileSync('git',['ls-files','-z'],{cwd:root,encoding:'utf8'}).split('\0').filter(Boolean);console.log(JSON.stringify(inspect(root,files)));}catch(e){console.error(e.message);process.exitCode=1;}}
module.exports={LIMITS,publicMediaURL,localLogPath,readLog,validateAsset,inspect};
