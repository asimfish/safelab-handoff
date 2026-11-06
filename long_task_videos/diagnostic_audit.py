"""Independent stratified20 raw audit for observed task7 other/stuck refinements."""
from pathlib import Path
import json,collections,math,random,concurrent.futures,hashlib
W=Path(__file__).parent;D=json.loads((W/'TASK7_DIAGNOSTICS.json').read_text());BASE={r['case_id']:r for r in json.loads((W/'TASK7_FIXED_ALL.json').read_text())};candidates=[r for r in D['cases']if r.get('subclass')];chosen={}
for key in sorted(set((r['method'],r['subclass'])for r in candidates)):
 r=min((r for r in candidates if(r['method'],r['subclass'])==key),key=lambda r:(r['scene_index'],r['case_id']));chosen[r['case_id']]=r
for r in candidates:
 if r['v11_order_deviations']:chosen[r['case_id']]=r
rest=sorted([r for r in candidates if r['case_id']not in chosen],key=lambda r:r['case_id'])
for r in random.Random(1263).sample(rest,20-len(chosen)):chosen[r['case_id']]=r
assert len(chosen)==20
def has_support(actors,target):return any(('/Balance/'in a if target=='pan'else a.endswith('/'+target)or'/'+target+'/'in a)for a in actors)
def hand(a):return '/Robot/'in a and any(x in a.lower()for x in ['hand','finger','palm'])
def check(d):
 c=BASE[d['case_id']];sc=json.loads(Path(c['source_scene']['file']).read_text());origin=sc['env_origins'][0];supports=sc['source_profile']['scene']['supports'];tol=min(.075,min(math.dist(a[:2],b[:2])for i,a in enumerate(supports.values())for j,b in enumerate(supports.values())if j>i)/2-.005);wt={e['object']:e['tick']for e in c['outcomes']['v1.3']['summary']['events']};firstweigh=min(wt.values(),default=10**12);touches={k:[]for k in'ABCD'};returns=set();tail=collections.deque(maxlen=1201);h=hashlib.sha256();last=None
 for b in Path(c['source_raw']['file']).open('rb'):
  h.update(b);z=json.loads(b);tick=z['tick'];anyhand=False
  for i,key in enumerate('ABCD'):
   actors=[a['actor']for a in z['contacts']if a['object']==key and a.get('contact_count',0)>0];is_hand=any(hand(a)for a in actors);anyhand|=is_hand
   if is_hand:touches[key].append((tick,z['poses'][i][2]))
   if key in wt and tick>wt[key]:
    p=z['poses'][i];xy=[p[j]-origin[j]for j in range(2)];near=min(supports,key=lambda k:math.dist(xy,supports[k][:2]));q=p[3:];up=1-2*(q[1]**2+q[2]**2)/sum(x*x for x in q)
    if near=='pad_'+key and math.dist(xy,supports[near][:2])<=tol and has_support(actors,near)and up>=.8:returns.add(key)
  tail.append((tick,z.get('q13'),anyhand));last=z
 assert h.hexdigest()==c['source_raw']['sha256'];groups={};failed={}
 for key,ts in touches.items():
  runs=[]
  for x in ts:
   if not runs or x[0]-runs[-1][-1][0]>30:runs.append([])
   runs[-1].append(x)
  qualified=[r for r in runs if len(r)>=12 and last['tick']-r[-1][0]>=30];groups[key]=[r for r in runs if len(r)>=12];failed[key]=[r for r in qualified if r[0][0]>=firstweigh and max(z for _,z in r)-r[0][1]<.02]
 q=[r[1][:7]for r in tail if r[1]];armrange=max((max(v)-min(v)for v in zip(*q)),default=99);diff=[[a-b for a,b in zip(y,x)]for x,y in zip(q,q[1:])];reversals=sum(any(a*b<0 and abs(a)>.0002 and abs(b)>.0002 for a,b in zip(x,y))for x,y in zip(diff,diff[1:]));nohand=all(not r[2]for r in tail);sub=d['subclass'];detail={}
 if sub=='later_grasp_retries':
  key=d['evidence']['object'];assert len(failed[key])==d['evidence']['failed_attempts']and len(failed[key])>=2 and key not in wt;detail={'object':key,'failed_attempts':len(failed[key]),'attempt_ranges':[[r[0][0],r[-1][0],max(z for _,z in r)-r[0][1]]for r in failed[key]]}
 elif sub=='weighed_no_return':
  key=d['evidence']['object'];assert key in wt and key not in returns;detail={'object':key,'weighed_tick':wt[key],'own_pad_support_after_weigh_observed':False,'not_a_v13_requirement':True}
 elif sub=='moving_without_cup_contact':
  assert nohand and armrange>=.01 and reversals>=12;detail={'last10s_hand_cup_contact':False,'arm_range_rad':armrange,'arm_reversal_ticks':reversals,'hand_world_position_not_recorded':True}
 elif sub=='stopped_after_k':assert armrange<.01;detail={'arm_range_rad':armrange}
 elif sub=='distance_unresolved':
  key=d['next_v13_candidate'];assert key not in wt;p=last['poses']['ABCD'.index(key)];local=[p[j]-origin[j]for j in range(3)];distance=math.dist(local[:2],supports['pan'][:2]);reported=next(v['xy_m']for v in d['terminal_distances']if v['object']==key);assert abs(distance-reported)<1e-9;detail={'object':key,'target':'pan','terminal_xy_m':distance,'unique_next_object_required_by_v13':False}
 elif sub=='contact_then_no_progress':raise AssertionError('New collision class must add an independent contact-window audit before publication')
 order=''.join('ABCD'[int(x)-1]for x in c['case_id'].split('_o')[-1].split('_')[0]);order_checks=[]
 for ev in d['v11_order_deviations']:
  key=ev['object'];run=next(r for r in groups[key]if r[0][0]<=ev['tick']<=r[-1][0]);phase=sum(e['tick']<=run[0][0]for e in c['outcomes']['v1.1']['summary'].get('events',[]));expected=order[min(phase//2,3)];assert key!=expected and expected==ev['expected_v11'];assert max(z for t,z in run if t<=ev['tick'])-run[0][1]>=.02;order_checks.append({'object':key,'expected_v11':expected,'tick':ev['tick'],'order_diagnostic_only_not_v13_failure':True})
 return {'case_id':d['case_id'],'method':d['method'],'scene_index':d['scene_index'],'parent_reason':d['parent_reason'],'subclass':sub,'label':d['subclass_label'],'passed':True,'raw_sha256':h.hexdigest(),'evidence':detail,'v11_order_checks':order_checks}
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=4)as p:rows=list(p.map(check,chosen.values()))
 out={'schema':'task7-observation-audit-v1','passed':True,'cases':rows,'selection':'One smallest scene_index per nonempty method×subclass; all v1.1-order-deviation cases; fill to20 with seed1263. No fabricated coverage for unobserved classes.','sample_seed':1263,'counts':D['counts'],'rule_sha256':D['rules_sha256'],'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limitations':['v1.3 is unordered and does not require returning cups; those observations refer only to v1.1 diagnostics','hand world positions and hand-to-balance contact are not recorded; do not claim empty-space location, hand distance or unobserved robot-scale collision','0 stopped/collision rule matches means no supported example, not proof no collision happened']};(W/'TASK7_DIAG_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('PASS20 stratified independent raw checks',flush=True)
