"""Bounded CPU rescore; large traces are read, never copied or rewritten."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import argparse,collections,gzip,hashlib,io,json,os,tarfile,time,traceback
import numpy as np
from relaxed_five import score,SEQUENCE,PARAMETERS
try:
    import orjson
    decode=orjson.loads
except ImportError:
    decode=json.loads

ROOT=Path(__file__).resolve().parent
ALLOWED='/projects/a02012413/buckets/zenith-a02012413/liyufeng/'

def save(path,value):
    pending=path.with_suffix(path.suffix+'.pending')
    pending.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n')
    pending.replace(path)

def load_source(item):
    if item.get('must_be_unknown_reason'):
        raise ValueError(item['must_be_unknown_reason'])
    if item['input_type']=='direct':
        scene=json.loads(Path(item['scene_contract']).read_text())
        path=Path(item['trace'])
        if not path.is_file():path=Path(str(path)+'.gz')
        return scene,gzip.open(path,'rb') if path.suffix=='.gz' else path.open('rb')
    path=Path(item['archive_path'])
    if not str(path).startswith(ALLOWED):raise ValueError('archive outside owned approved bucket')
    if path.stat().st_size!=item['archive_bytes'] or path.stat().st_size>256<<20:
        raise ValueError('archive size mismatch or exceeds CPU buffer limit')
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=item['archive_sha256']:
        raise ValueError('archive integrity mismatch')
    scene=None;trace=None
    with tarfile.open(fileobj=io.BytesIO(data),mode='r|gz')as tar:
        count=0
        for member in tar:
            count+=1
            if count>10000:raise ValueError('archive member count limit')
            name=Path(member.name)
            if name.is_absolute() or '..'in name.parts or not member.isfile():
                raise ValueError('unsafe archive member')
            if name.name=='SCENE_CONTRACT.json':
                if member.size>4<<20:raise ValueError('scene metadata too large')
                scene=json.loads(tar.extractfile(member).read())
            if name.name=='physical_120hz.jsonl.gz':
                if member.size>128<<20:raise ValueError('trace compressed size limit')
                trace=tar.extractfile(member).read()
    if scene is None or trace is None:raise ValueError('raw trace/scene missing from archive')
    return scene,gzip.GzipFile(fileobj=io.BytesIO(trace))

def negative_windows(profile,p,support,clear,ticks,recorded_phase,origin):
    """Actual recorded-state rejection probes; no fabricated trajectories."""
    from scipy.spatial.transform import Rotation
    p=p.copy();p[:,:,:3]-=origin
    up=Rotation.from_quat(np.roll(p[:,:,3:].reshape(-1,4),-1,axis=1)).apply(np.tile([0,0,1],(len(p)*3,1)))[:,2].reshape(-1,3)
    found={}
    for stage,(key,target)in enumerate(SEQUENCE):
        ix='ABC'.index(key);bottom=profile['scene'].get('object_bottom_offsets',{}).get(key,profile['scene']['half_height'])
        center=np.array(profile['scene']['supports'][target])+[0,0,bottom]
        xy=np.linalg.norm(p[:,ix,:2]-center[:2],axis=1);dz=np.abs(p[:,ix,2]-center[2]);supported=support[:,stage]|(dz<=.01)
        active=recorded_phase==stage
        masks={'held':active&(xy<=.05)&(up[:,ix]>=.9)&supported&~clear[:,ix],
               'tilted':active&(up[:,ix]<.9),
               'outside':active&(xy>.05)&(up[:,ix]>=.9)&supported&clear[:,ix]}
        placed=(xy<=.05)&(up[:,ix]>=.9)&supported&clear[:,ix]
        for kind,mask in masks.items():
            if kind in found:continue
            starts=np.flatnonzero(np.diff(np.r_[False,mask,False].astype(int))==1)
            ends=np.flatnonzero(np.diff(np.r_[False,mask,False].astype(int))==-1)
            valid=np.flatnonzero(ends-starts>=12)
            if not len(valid):continue
            j=int(valid[0]);a=int(starts[j]);b=a+12
            assert not placed[a:b].any()
            found[kind]={'stage':stage,'object':key,'tick_start':int(ticks[a]),'tick_end':int(ticks[b-1]),'ticks':12,'rejected_all_12_ticks':True,'xy_range_m':[float(xy[a:b].min()),float(xy[a:b].max())],'upright_cos_range':[float(up[a:b,ix].min()),float(up[a:b,ix].max())],'height_error_range_m':[float(dz[a:b].min()),float(dz[a:b].max())],'any_robot_contact':bool((~clear[a:b,ix]).any())}
    return found

def evaluate(item):
    base={k:item.get(k)for k in ['id','run_id','role','variant','method','checkpoint_step','execution_horizon','layout','seed','repeat','condition','scene_index']}
    try:
        scene,stream=load_source(item)
        poses=[];ticks=[];supports=[];clear=[];no_fingers=[];phases=[]
        with stream:
            for raw in stream:
                if len(poses)>=100000 or len(raw)>2<<20:raise ValueError('physical trace size limit')
                r=decode(raw);poses.append(r['poses']);ticks.append(r['tick']);phases.append(r['physical_phase'])
                sup=[False]*5;free=[True]*3;fingers=[True]*3
                attachment=r.get('attachment');attached=attachment.get('attached_object')if isinstance(attachment,dict)else None
                if attached in 'ABC' if isinstance(attached,str) else False:free['ABC'.index(attached)]=False
                for contact in r['contacts']:
                    if contact['contact_count']<=0:continue
                    key=contact['object'];actor=contact['actor']
                    if key not in ['A','B','C']:continue
                    ix='ABC'.index(key)
                    if '/Robot/'in actor:
                        free[ix]=False
                        if '/hand2_'in actor:fingers[ix]=False
                    for j,(obj,target)in enumerate(SEQUENCE):
                        if obj==key and '/'+target in actor:sup[j]=True
                supports.append(sup);clear.append(free);no_fingers.append(fingers)
        p=np.asarray(poses,dtype=np.float32);s=np.asarray(supports,dtype=bool);c=np.asarray(clear,dtype=bool);t=np.asarray(ticks)
        origin=np.asarray(scene['env_origins'][0]);profile=scene['source_profile']
        answers=score(profile,p,s,c,np.asarray(no_fingers,dtype=bool),t,origin=origin)
        prior=item.get('prior_metrics')or{}
        mismatch=[]
        for metric in ['strict_v1','placement_v1_1']:
            if metric in prior:
                old=prior[metric];new=answers[metric]
                if (bool(old['success']),old['physical_phase'])!=(new['success'],new['phase']):
                    mismatch.append({'metric':metric,'recorded':old,'recomputed':new})
        if mismatch:
            return {**base,'status':'compatibility_mismatch','mismatch':mismatch}
        neg=negative_windows(profile,p,s,c,t,np.asarray(phases),origin)
        # Report overlapping relaxed target disks without altering the frozen rule.
        centers={target:np.asarray(profile['scene']['supports'][target])[:2]for _,target in SEQUENCE}
        overlaps=[];names=list(centers)
        for i,x in enumerate(names):
            for y in names[i+1:]:
                distance=float(np.linalg.norm(centers[x]-centers[y]))
                if distance<.10:overlaps.append({'targets':[x,y],'distance_m':distance})
        return {**base,'status':'rescored','metrics':answers,'rows':len(t),'negative_windows':neg,'overlapping_target_disks':overlaps,'source_trace':item.get('trace')or item.get('archive_path'),'source_video':item.get('episode_root','')+'/third_person.mp4'if item.get('episode_root')else None}
    except Exception as e:
        return {**base,'status':'unknown','reason':type(e).__name__+':'+str(e),'traceback':traceback.format_exc(limit=2)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=3);parser.add_argument('--limit',type=int);args=parser.parse_args()
    rows=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())
    if args.limit:rows=rows[:args.limit]
    dest=ROOT/'cases';dest.mkdir(exist_ok=True)
    todo=[];count=collections.Counter();started=time.time()
    for r in rows:
        key=hashlib.sha256((r['role']+'::'+r['id']).encode()).hexdigest()[:24]
        r={**r,'result_key':key}
        if (dest/(key+'.json')).is_file():count['cached']+=1
        else:todo.append(r)
    with ProcessPoolExecutor(max_workers=args.workers)as pool:
        for item,result in zip(todo,pool.map(evaluate,todo,chunksize=1)):
            save(dest/(item['result_key']+'.json'),result);count[result['status']]+=1
            done=sum(count.values())
            if done%5==0 or done==len(rows):
                progress={'done':done,'target':len(rows),'counts':dict(count),'wall_s':time.time()-started,'CPU_only':True,'workers':args.workers,'new_simulations':0,'epoch':time.time()}
                save(ROOT/'PROGRESS.json',progress)
                print(json.dumps(progress),flush=True)
    save(ROOT/'DONE.json',{'complete':True,'target':len(rows),'counts':dict(count),'wall_s':time.time()-started,'CPU_only':True})

if __name__=='__main__':main()
