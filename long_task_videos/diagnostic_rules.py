"""Observable task7 failure refinement. Does not change either oracle verdict.
Contact attempt=hand contact >=12ticks then >=30ticks separated, failed if no20mm lift.
Later-cup retry requires >=2 such failures after >=1 cup was weighed.
Return-to-pad and wrong-object order are v1.1 diagnostics only: v1.3 is unordered
and credits weighing without requiring a return. No hand-world position is logged;
reported terminal distances are CUP-center XY to targets, never hand distances.
Collision flag requires new non-target balance/cup contact at speed>=.05m/s,
outside pan tolerance for balance contact, then>=5s with no further oracle progress.
"""
from pathlib import Path
import json,math,hashlib,collections,concurrent.futures,re,time,random
W=Path(__file__).parent;OUT=W/'task7_diagnostics';OUT.mkdir(exist_ok=True)
LABELS={'later_grasp_retries':'后续杯多次接触尝试未抬起','contact_then_no_progress':'非目标接触后无后续进展','weighed_no_return':'已上秤但未取回自身垫子（v1.1诊断）','stopped_after_k':'完成k杯后手臂停止运动','moving_without_cup_contact':'无杯接触的反复运动','distance_unresolved':'超时距离诊断 / 行为证据不足'}
def hand_actor(a):return '/Robot/'in a and any(t in a.lower()for t in ['hand','finger','palm'])
def support(actors,target):return any(('/Balance/'in a if target=='pan'else a.endswith('/'+target)or'/'+target+'/'in a)for a in actors)
def scan(c):
 p=OUT/(c['case_id']+'.json')
 if p.exists():return json.loads(p.read_text())
 if not c.get('source_raw'):return {'case_id':c['case_id'],'method':c['method'],'known':False}
 contract=json.loads(Path(c['source_scene']['file']).read_text());origin=contract['env_origins'][0];targets=contract['source_profile']['scene']['supports'];spacing=min(math.dist(a[:2],b[:2])for i,a in enumerate(targets.values())for j,b in enumerate(targets.values())if j>i);tol=min(.075,spacing/2-.005);events13=c['outcomes']['v1.3']['summary']['events'];events11=c['outcomes']['v1.1']['summary'].get('events',[]);order=c['case_id'].split('_o')[-1].split('_')[0]if '_o'in c['case_id']else '1234';order=''.join('ABCD'[int(x)-1]for x in order);weigh_ticks={e['object']:e['tick']for e in events13};allprogress=sorted(e['tick']for e in events13+events11);lastprogress=max(allprogress,default=125);firstweigh=min(weigh_ticks.values(),default=10**12);episodes={k:None for k in 'ABCD'};attempts={k:[]for k in 'ABCD'};returned={};lastcontact=None;lastposes=None;lasttick=None;priorcontacts=set();collisions=[];wrongorder=[];tail=collections.deque(maxlen=1201);initial=None;h=hashlib.sha256();n=0
 for b in Path(c['source_raw']['file']).open('rb'):
  h.update(b);z=json.loads(b);tick=z['tick'];poses=z['poses'];initial=initial or [p[2]for p in poses];n+=1;phase11=sum(t<=tick for t in [e['tick']for e in events11]);expected=order[min(phase11//2,3)];activekeys=[];present=set()
  for i,key in enumerate('ABCD'):
   actors=[a['actor']for a in z['contacts']if a['object']==key and a.get('contact_count',0)>0];hand=any(hand_actor(a)for a in actors);pworld=poses[i];local=[pworld[j]-origin[j]for j in range(3)];ds={k:math.dist(local[:2],v[:2])for k,v in targets.items()};near=min(ds,key=ds.get);q=pworld[3:];up=1-2*(q[1]**2+q[2]**2)/sum(x*x for x in q)
   if key in weigh_ticks and tick>weigh_ticks[key] and near=='pad_'+key and ds[near]<=tol and support(actors,near)and up>=.8:returned.setdefault(key,tick)
   ep=episodes[key]
   if hand:
    activekeys.append(key);lastcontact=(tick,key)
    if ep is None:ep={'start_tick':tick,'start_z':pworld[2],'contact_ticks':0,'off_ticks':0,'max_rise_m':0.,'v11_expected_object_at_start':expected,'lift_tick':None};episodes[key]=ep
    ep['contact_ticks']+=1;ep['off_ticks']=0;ep['max_rise_m']=max(ep['max_rise_m'],pworld[2]-ep['start_z'])
    if ep['lift_tick']is None and ep['max_rise_m']>=.02:
     ep['lift_tick']=tick
     if key!=ep['v11_expected_object_at_start']:wrongorder.append({'tick':tick,'object':key,'expected_v11':ep['v11_expected_object_at_start'],'order_diagnostic_only':True})
   elif ep is not None:
    ep['off_ticks']+=1
    if ep['off_ticks']>=30:
     if ep['contact_ticks']>=12:attempts[key].append({**ep,'end_tick':tick-29,'failed_no_20mm_lift':ep['max_rise_m']<.02})
     episodes[key]=None
   speed=math.dist(pworld[:3],lastposes[i][:3])*120 if lastposes else 0
   for actor in actors:
    pair=(key,actor);present.add(pair)
    cup_other=bool(re.search(r'/(?:beaker|cup)[_/]?([ABCD])(?:/|$)',actor,re.I))and not actor.endswith(key)
    non_target_balance='/Balance/'in actor and ds['pan']>tol+.02
    if pair not in priorcontacts and (cup_other or non_target_balance)and speed>=.05 and not any(abs(tick-t)<=60 for t in allprogress):collisions.append({'tick':tick,'object':key,'actor':actor,'speed_m_s':speed,'xy_to_pan_m':ds['pan'],'kind':'cup_contact'if cup_other else'offcenter_balance_contact'})
  if z.get('q13'):tail.append({'tick':tick,'q':z['q13'],'hand_contacts':activekeys})
  priorcontacts=present;lastposes=poses;lasttick=tick
 assert h.hexdigest()==c['source_raw']['sha256'];last=tick;duration=(tick-125)/120;phase13=c['outcomes']['v1.3']['phase'];phase11=c['outcomes']['v1.1'].get('phase',0);current_v11=order[min(phase11//2,3)];target_v11='pad_'+current_v11 if phase11%2 else'pan';unfinished=[k for k in order if k not in weigh_ticks];next13=lastcontact[1]if lastcontact and lastcontact[1]in unfinished else unfinished[0]if unfinished else None
 distances=[]
 for i,key in enumerate('ABCD'):
  local=[poses[i][j]-origin[j]for j in range(3)];target='pan'if key not in weigh_ticks else'pad_'+key;xy=math.dist(local[:2],targets[target][:2]);distances.append({'object':key,'target':target,'xy_m':xy,'position_local':local,'target_xyz':targets[target],'weighed':key in weigh_ticks,'returned_after_weigh':key in returned,'is_next_v13_candidate':key==next13,'is_expected_v11':key==current_v11})
 armrange=max((max(v)-min(v)for v in zip(*(r['q'][:7]for r in tail))),default=99);rev=0
 qs=[r['q'][:7]for r in tail];delta=[[a-b for a,b in zip(q,p)]for p,q in zip(qs,qs[1:])]
 rev=sum(any(a*b<0 and abs(a)>.0002 and abs(b)>.0002 for a,b in zip(x,y))for x,y in zip(delta,delta[1:]));nocontact=all(not r['hand_contacts']for r in tail);retry_candidates=[]
 for key,ats in attempts.items():
  failed=[e for e in ats if e['failed_no_20mm_lift']and e['start_tick']>=firstweigh]
  if key in unfinished and order.index(key)>0 and len(failed)>=2:retry_candidates.append({'object':key,'k_v11':order.index(key)+1,'failed_attempts':len(failed),'episodes':failed})
 unreturned=[k for k in order[:-1]if k in weigh_ticks and k not in returned];collision_candidates=[e for e in collisions if e['tick']>lastprogress and last-e['tick']>=600]
 subclass=None;proof=None
 if c['reason']in ['other','stuck']:
  if retry_candidates:subclass='later_grasp_retries';proof=max(retry_candidates,key=lambda e:e['failed_attempts'])
  elif collision_candidates and(armrange<.01 or nocontact):subclass='contact_then_no_progress';proof=collision_candidates[-1]
  elif current_v11 in unreturned and phase11%2:subclass='weighed_no_return';proof={'object':current_v11,'weigh_tick':weigh_ticks[current_v11],'no_return_observed':True,'v11_diagnostic_only':True,'v13_requires_return':False}
  elif armrange<.01 and phase13>0:subclass='stopped_after_k';proof={'completed_cups':phase13,'last10s_arm_max_range_rad':armrange}
  elif nocontact and armrange>=.01 and rev>=12:subclass='moving_without_cup_contact';proof={'completed_cups':phase13,'last10s_no_cup_hand_contact':True,'arm_reversal_ticks':rev,'arm_max_range_rad':armrange,'hand_world_position_not_recorded':True}
  else:subclass='distance_unresolved';proof={'completed_cups':phase13,'next_v13_candidate':next13,'distance':next((x for x in distances if x['object']==next13),None),'unique_next_object_required_by_v13':False}
 result={'case_id':c['case_id'],'method':c['method'],'scene_index':c['scene_index'],'known':True,'parent_reason':c['reason'],'subclass':subclass,'subclass_label':LABELS.get(subclass),'evidence':proof,'attempt_counts':{k:{'qualified_contacts':len(ats),'failed_no_lift':sum(e['failed_no_20mm_lift']for e in ats),'active_attempt_at_end':episodes[k]is not None}for k,ats in attempts.items()},'attempt_episodes':attempts,'weighed_objects':sorted(weigh_ticks),'returned_after_weigh':returned,'unreturned_v11_required_objects':unreturned,'v11_order_deviations':wrongorder,'v11_order_deviation_is_not_v13_failure':True,'terminal_distances':distances,'next_v13_candidate':next13,'v11_next_object':current_v11,'v11_next_target':target_v11,'last10s_arm_range_rad':armrange,'last10s_arm_reversal_ticks':rev,'last10s_no_cup_hand_contact':nocontact,'collision_observations':collisions,'raw_sha256':h.hexdigest(),'source_scene_sha256':c['source_scene']['sha256'],'duration_s':duration,'last_progress_tick':lastprogress,'rules_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};p.write_text(json.dumps(result,separators=(',',':')));return result
if __name__=='__main__':
 cs=json.loads((W/'TASK7_FIXED_ALL.json').read_text());out=[];errors=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4)as pool:
  fs={pool.submit(scan,c):c for c in cs}
  for f in concurrent.futures.as_completed(fs):
   try:out.append(f.result())
   except Exception as e:errors.append({'case_id':fs[f]['case_id'],'error':str(e)})
   (W/'TASK7_DIAG_STATE.json').write_text(json.dumps({'closed':len(out),'errors':errors,'expected':len(cs),'epoch':time.time()}))
 assert not errors,errors[:3]
 counts={m:dict(collections.Counter(r['subclass']for r in out if r.get('subclass')and r['method']==m))for m in sorted(set(r['method']for r in out))};(W/'TASK7_DIAGNOSTICS.json').write_text(json.dumps({'schema':'task7-diagnostic-refinement-v1','rules_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'labels':LABELS,'counts':counts,'cases':out},separators=(',',':')));print(json.dumps(counts),flush=True)
