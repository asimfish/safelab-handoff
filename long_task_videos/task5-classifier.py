"""Task5-specific fixed ordered-placement replay and release classifier.
A->temporary_A,B->temporary_B,C->target_C,A->pad_A,B->pad_B.
Source v1.1/v1.2 remain distinct. v1.3 is not published and is NEVER fabricated.
Correct release advancing either available protocol is exempt. Targets are latched
before stage advancement; later regrasp/correct support clears an old candidate.
"""
from pathlib import Path
import sys,json,math,hashlib,collections,concurrent.futures,time
W=Path(__file__).parent;sys.path.insert(0,str(W/'scipy_deps'))
S=Path('/project_a02012413/public/liyufeng/safelab_task5_v12_relaxed_20261105')
ORACLE_SHA='245a24be8cc7d8fc820397d299abffcf896b29d619034ae95082da18e719cc94'
assert hashlib.sha256((S/'relaxed_five.py').read_bytes()).hexdigest()==ORACLE_SHA
sys.path.insert(0,str(S));from relaxed_five import score,SEQUENCE,PARAMETERS
import numpy as np
from failure_rules import LABELS
OUT=W/'task5_scan_v2';OUT.mkdir(exist_ok=True);D=json.loads((W/'task5_sources.json').read_text());REF={r['case_id']:r for r in json.loads((W/'TASK5_EXTRACTED.json').read_text())}
def sup(actors,target):return any('/'+target in a for a in actors)
def one(r):
 cid=r['id'];dest=OUT/(cid+'.json')
 if dest.exists():return json.loads(dest.read_text())
 ref=REF[cid];method={'new30':'mem0_new30','ours30':'ours30','pi05_40k':'pi05_40k','memoryvla30':'memoryvla_30k'}[r['variant']]
 c={'task':5,'method':method,'horizon':r['execution_horizon'],'checkpoint':r['checkpoint_step'],'case_id':cid,'scene_index':r['scene_index'],'seed':r['seed'],'source_input_camera':'third_person','source_authority':'producer v1.1/v1.2 and exact frozen ordered-five CPU replay; v1.3 unpublished','source_oracle_sha256':ORACLE_SHA,'classification_version':'long-task-failure-v2','v11_total':5,'v13_total':5,'selection':[]}
 if ref.get('known')is False:
  c.update(reason='unknown',reason_label=LABELS['unknown'],failure_time=None,evidence=ref['unknown_reason'],features={'sha_verified':False},outcomes={'v1.1':{'verdict':'U','phase':None,'success':None},'v1.2':{'verdict':'U','phase':None,'success':None},'v1.3':{'verdict':'unpublished','phase':None,'success':None}},source_raw=None,trace=[],source_video=None,source_video_exists=False);dest.write_text(json.dumps(c));return c
 raw=Path(ref['raw']);contract=json.loads(Path(ref['scene']).read_text());profile=contract['source_profile'];origin=contract['env_origins'][0];supports=profile['scene']['supports'];poses=[];ticks=[];supported=[];clear=[];nofingers=[];h=hashlib.sha256()
 for b in raw.open('rb'):
  h.update(b);z=json.loads(b);poses.append(z['poses']);ticks.append(z['tick']);ss=[False]*5;free=[True]*3;nf=[True]*3;att=z.get('attachment');ak=att.get('attached_object')if isinstance(att,dict)else None
  if isinstance(ak,str)and ak in 'ABC':free['ABC'.index(ak)]=False
  for a in z['contacts']:
   if a.get('contact_count',0)<=0 or a['object']not in'ABC':continue
   k=a['object'];i='ABC'.index(k);actor=a['actor']
   if '/Robot/'in actor:
    free[i]=False
    if '/hand2_'in actor:nf[i]=False
   for j,(obj,target)in enumerate(SEQUENCE):
    if obj==k and'/'+target in actor:ss[j]=True
  supported.append(ss);clear.append(free);nofingers.append(nf)
 p=np.asarray(poses,dtype=np.float32);t=np.asarray(ticks);answers=score(profile,p,np.asarray(supported),np.asarray(clear),np.asarray(nofingers),t,origin=np.asarray(origin))
 for key in ['strict_v1','placement_v1_1','placement_v1_2_relaxed']:
  assert answers[key]==r['metrics'][key],'source full metric/events mismatch '+key
 del p,poses,supported,clear,nofingers
 e11=answers['placement_v1_1']['events'];e12=answers['placement_v1_2_relaxed']['events'];events=e11+e12;progress_ticks=[a['tick']for a in events];first=ticks[0];rawsha=h.hexdigest();trace=[];lastphase=None;initial=None;lift=[False]*3;robots_before=[False]*3;grasp=[None]*3;pending={};wrong={};drop={};high=[None]*3;held=[None]*3;tail=collections.deque(maxlen=1201);qd=collections.deque(maxlen=1200);prevq=None;guard=None;n=0;firstmax=0
 for b in raw.open('rb'):
  z=json.loads(b);tick=z['tick'];tt=(tick-first)/120;n+=1;ps=z['poses'];initial=initial or [a[2]for a in ps];ph11=sum(a['tick']<=tick for a in e11);ph12=sum(a['tick']<=tick for a in e12);active_phase=min(max(ph11,ph12),4)
  if n%120==1 or(ph11,ph12)!=lastphase:trace.append({'t':tt,'tick':tick,'phase11':ph11,'phase12':ph12,'phase13':None});lastphase=(ph11,ph12)
  for i,key in enumerate('ABC'):
   po=ps[i];local=[po[j]-origin[j]for j in range(3)];ds={k:math.dist(local[:2],a[:2])for k,a in supports.items()};nearest=min(ds,key=ds.get);q=po[3:];up=1-2*(q[1]**2+q[2]**2)/sum(v*v for v in q);actors=[a['actor']for a in z['contacts']if a['object']==key and a.get('contact_count',0)>0];robot=any('/Robot/'in a for a in actors);lift[i]=lift[i]or(robot and po[2]-initial[i]>=.02)
   if i==0:firstmax=max(firstmax,po[2]-initial[i])
   if guard is None and(up<.5 or local[2]<profile['scene']['table_top']-.1):guard={'tick':tick,'object':key,'upright':up,'fell':local[2]<profile['scene']['table_top']-.1}
   # A genuine later source phase advance or supported intended return cancels history.
   if robot:wrong.pop(key,None);drop.pop(key,None)
   if any(a['tick']==tick and a['object']==key for a in events):wrong.pop(key,None);drop.pop(key,None)
   if robot and not robots_before[i]:grasp[i]={'tick':tick,'phase_before':active_phase,'expected_object':SEQUENCE[active_phase][0],'expected_target':SEQUENCE[active_phase][1]};pending.pop(key,None)
   if not robot and robots_before[i]and lift[i]and grasp[i]:pending[key]={**grasp[i],'release_tick':tick,'object':key}
   if not robot and key in pending and tick-pending[key]['release_tick']>=30:
    e=pending.pop(key);target=e['expected_target'];advanced=[a for a in events if a['object']==key and a['tick']>=e['tick']]
    e.update(confirm_tick=tick,nearest=nearest,distances=ds,position_local=local,contacts=actors,advances=advanced)
    if not advanced and sup(actors,nearest)and(nearest!=target or key!=e['expected_object'])and up>=.8:wrong[key]=e
   # Correct support at the latched intended target cancels an earlier error.
   if key in wrong and nearest==wrong[key]['expected_target']and sup(actors,nearest)and key==wrong[key]['expected_object']:wrong.pop(key,None)
   if robot:high[i]=(tick,po[2])
   elif lift[i]and high[i]and tick-high[i][0]<=120 and high[i][1]-po[2]>=.03 and min(ds.values())>.05 and not any(sup(actors,k)for k in supports):drop[key]={'tick':tick,'object':key};high[i]=None
   current_key,current_target=SEQUENCE[min(ph11,4)];inside=key==current_key and ds[current_target]<=.05
   validheld=robot and inside and not sup(actors,current_target);held[i]=held[i]if validheld and held[i]is not None else tick if validheld else None;robots_before[i]=robot
  q=z.get('q13')
  if q:
   tail.append(q)
   if prevq is not None:qd.append([a-b for a,b in zip(q,prevq)])
   prevq=q
 if trace[-1]['tick']!=tick:trace.append({'t':tt,'tick':tick,'phase11':ph11,'phase12':ph12,'phase13':None})
 assert ph11==answers['placement_v1_1']['phase']and ph12==answers['placement_v1_2_relaxed']['phase'];ranges=max((max(v)-min(v)for v in zip(*tail)),default=99);rev=sum(any(a*b<0 and abs(a)>.0002 and abs(b)>.0002 for a,b in zip(x,y))for x,y in zip(qd,list(qd)[1:]));lastprogress=max(progress_ticks,default=first);decisive=[(e['release_tick'],'wrong_target','稳定释放到非期望目标/对象；之后无源协议推进且未纠正')for e in wrong.values()]+[(e['tick'],'dropped','抬起后无手接触、下降≥30mm且不在任一命名目标，之后未纠正')for e in drop.values()]
 if answers['placement_v1_1']['success']:reason,failtick,evidence='success',None,'冻结v1.1整任务成功（v1.3未发布）'
 elif guard:reason,failtick,evidence='toppled',guard['tick'],'冻结v1.1灾难保护触发；该协议从此停止评分，不把后续画面伪装成恢复'
 elif decisive:failtick,reason,evidence=max(decisive,key=lambda a:a[0])
 elif any(a is not None and tick-a>=240 for a in held):reason,failtick,evidence='no_release',lastprogress,'末2秒在当前放置目标上方持续持握；标记最后有效进展'
 elif ph11==0 and firstmax<.02:reason,failtick,evidence='no_grasp',lastprogress,'完整原始日志、首物体抬升不足20mm、v1.1阶段0'
 elif ranges<.01 or rev>=12:reason,failtick,evidence='stuck',lastprogress,'末10秒停滞或反向运动；标记最后有效进展'
 else:reason,failtick,evidence='other',lastprogress,'无可验证专属不可恢复事件；标记最后有效进展'
 c.update(reason=reason,reason_label=LABELS[reason],failure_time=(failtick-first)/120 if failtick is not None else None,evidence=evidence,source_raw={'file':str(raw),'sha256':rawsha,'rows':n},source_scene={'file':ref['scene'],'sha256':hashlib.sha256(Path(ref['scene']).read_bytes()).hexdigest()},source_video=ref['video'],source_video_exists=True,video_origin_tick=None,raw_origin_tick=first,source_frameclock_qualified=False,outcomes={'v1.1':dict(answers['placement_v1_1'],verdict='S'if answers['placement_v1_1']['success']else'F'),'v1.2':dict(answers['placement_v1_2_relaxed'],verdict='S'if answers['placement_v1_2_relaxed']['success']else'F'),'v1.3':{'verdict':'unpublished','phase':None,'success':None,'N':5}},features={'sha_verified':True,'oracle_replayed':True,'phase11_max':ph11,'phase12_max':ph12,'first_max_rise':firstmax,'duration':tt,'tail_q_range':ranges,'q_reversals':rev},trace=trace,unresolved_wrong=list(wrong.values()),guard_event=guard)
 dest.write_text(json.dumps(c,separators=(',',':')));return c
if __name__=='__main__':
 rows=D['rows'];out=[];err=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4)as p:
  fs={p.submit(one,r):r for r in rows}
  for f in concurrent.futures.as_completed(fs):
   try:out.append(f.result())
   except Exception as e:err.append({'case':fs[f]['id'],'error':str(e)})
   (W/'TASK5_SCAN_STATE.json').write_text(json.dumps({'closed':len(out),'expected':600,'errors':err,'epoch':time.time()}))
 assert not err,err[:5]
 (W/'TASK5_FIXED_ALL.json').write_text(json.dumps(out,separators=(',',':')));print('scored600 including31unknown',flush=True)
