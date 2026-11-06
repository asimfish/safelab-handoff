from pathlib import Path
import json,hashlib,math,concurrent.futures,collections
W=Path(__file__).parent
allrows={t:json.loads((W/('TASK'+str(t)+'_FIXED_ALL.json')).read_text())for t in [5,7,10]}
SEQUENCE=[('A','temporary_A'),('B','temporary_B'),('C','target_C'),('A','pad_A'),('B','pad_B')]
def audit(c):
 task=c['task'];checks=[];wanted=c['unresolved_wrong'];segments={}
 for i,e in enumerate(wanted):
  start=e['tick']if task==5 else e.get('grasp_start',e['tick']);end=e.get('release_tick',e['tick']);segments[i]={'start':start,'end':end,'first':None,'max_motion':0.,'max_lift':0.}
 h=hashlib.sha256()
 for b in Path(c['source_raw']['file']).open('rb'):
  h.update(b);z=json.loads(b)
  for i,sg in segments.items():
   if sg['start']<=z['tick']<=sg['end']:
    p=z['poses'][('ABC'if task==5 else'ABCD'if task==7 else'ABCDE').index(wanted[i]['object'])][:3];sg['first']=sg['first']or p;sg['max_motion']=max(sg['max_motion'],math.dist(p,sg['first']));sg['max_lift']=max(sg['max_lift'],p[2]-sg['first'][2])
 assert h.hexdigest()==c['source_raw']['sha256']
 kept=[]
 for i,e in enumerate(wanted):
  sg=segments[i];release=dict(e);good_motion=sg['first']is not None and sg['max_motion']>=.02;expected=[]
  if task==5:
   for protocol in ['v1.1','v1.2']:
    ph=sum(v['tick']<=sg['start']for v in c['outcomes'][protocol]['events']);expected.append({'protocol':protocol,'phase':ph,'object':SEQUENCE[min(ph,4)][0],'target':SEQUENCE[min(ph,4)][1]})
   correct_for_source=any(x['object']==e['object']and x['target']==e['nearest']for x in expected)
  else:correct_for_source=False
  retain=good_motion and not correct_for_source
  check={'case_id':c['case_id'],'task':task,'method':c['method'],'horizon':c['horizon'],'scene_index':c['scene_index'],'object':e['object'],'segment_start':sg['start'],'release_tick':sg['end'],'max_motion_m':sg['max_motion'],'max_lift_m':sg['max_lift'],'expected_by_protocol':expected,'correct_for_available_source':correct_for_source,'retained_wrong_release':retain,'raw_sha256':h.hexdigest()};checks.append(check)
  if retain:release['genuine_segment_proof']=check;kept.append(release)
 original=c['reason'];c['release_segment_audit']=checks
 if original=='wrong_target'and not kept:
  events=[]
  for p in c['outcomes'].values():events.extend(p.get('events',p.get('summary',{}).get('events',[])))
  last=max((e['tick']for e in events),default=c['raw_origin_tick']);c.update(reason='other',reason_label='其他（释放诊断撤回）',failure_time=max(0,(last-c['raw_origin_tick'])/120),evidence='撤回放错诊断：该接触段物体移动不足20mm，或释放目标符合一个已发布源协议的当前放置项。不能把接触闪断或跨协议阶段差当作搬运放错。',classification_version='long-task-failure-v3',diagnosis_changed_from=original)
 c['unresolved_wrong']=kept;return c,checks
if __name__=='__main__':
 jobs=[c for rs in allrows.values()for c in rs if c['reason']=='wrong_target'];updates={};checks=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4)as ex:
  for c,a in ex.map(audit,jobs):updates[c['case_id']]=c;checks+=a
 for t,rs in allrows.items():
  out=[updates.get(c['case_id'],c)for c in rs];(W/('TASK'+str(t)+'_SEGMENT_REVIEW_V3.json')).write_text(json.dumps(out,separators=(',',':')));print(t,'counts',dict(collections.Counter(c['reason']for c in out)),flush=True)
 (W/'RELEASE_SEGMENT_AUDIT_V3.json').write_text(json.dumps({'criteria':'Current source protocol targets considered independently; genuine per-contact-segment object motion≥20mm. Below threshold labels conservatively withdrawn; this is not a claim of no physical failure.','cases':checks},separators=(',',':')));print('reviewed',len(jobs),flush=True)
