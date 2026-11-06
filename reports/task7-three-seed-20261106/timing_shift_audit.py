"""CPU audit of sealed actual predictions; never invokes a model or simulator."""
from pathlib import Path
import hashlib,json,math,os,time,traceback
import numpy as np

S=Path('/project_a02012413/public/liyufeng/safelab_mem0_7weigh_eval_20261027')
P=S/'low_sr_diagnostic_traininit_p1_v1'
O=S/'inference_1400_cpu_20261106/timing_shift'
D=Path('/tmp/t939_AB_A20_data_first2_v1')
EPISODES=list(range(10))+list(range(50,60))
SHIFTS=list(range(-8,9))

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def dump(p,d):
 q=p.with_suffix(p.suffix+'.pending')
 q.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
 q.replace(p)

def ref(p):return dict(file=str(p),sha256=sha(p),bytes=p.stat().st_size)

def new():return dict(n=0,sse=np.zeros(13,dtype=np.float64))
def add(m,err):m['n']+=len(err);m['sse']+=np.square(err).sum(axis=0)
def finish(m):
 n=m['n'];s=m['sse']
 return dict(n=n,arm_RMSE_rad=float(np.sqrt(s[:7].sum()/(n*7))) if n else None,
             hand_RMSE_rad=float(np.sqrt(s[7:].sum()/(n*6))) if n else None,
             all_RMSE_rad=float(np.sqrt(s.sum()/(n*13))) if n else None,
             joint_RMSE_rad=np.sqrt(s/n).tolist() if n else None,
             squared_error_sum_joint_rad2=s.tolist())

def svg(rows):
 colors=['#2864bc','#c4482b']; W,H=1000,570
 out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
      '<rect width="100%" height="100%" fill="white"/>',
      '<style>text{font-family:sans-serif;fill:#222;font-size:14px}.title{font-size:19px}</style>',
      '<text class="title" x="30" y="28">Task 7: first predicted target vs shifted training labels</text>',
      '<text x="30" y="51">20 fixed episodes; same saved predictions, common frames; positive shift = later label</text>']
 for col,grid in enumerate(['policy_15Hz_rows','converted_120Hz_control_ticks']):
  for rno,part in enumerate(['arm','hand']):
   x0=70+col*490;y0=85+rno*230;w=385;h=155
   curves=[q for q in rows if q['grid']==grid and q['group']=='all']
   ym=max(v[f'{part}_RMSE_rad'] for q in curves for v in q['curve'])*1.08
   ym=max(ym,1e-6)
   out += [f'<text x="{x0}" y="{y0-12}">{grid}, {part} RMSE (rad)</text>',
           f'<path d="M{x0},{y0} v{h} h{w}" fill="none" stroke="#444"/>']
   for value in [0,ym/2,ym]:
    yy=y0+h-h*value/ym
    out += [f'<text x="{x0-55}" y="{yy+5}">{value:.4f}</text>',f'<path d="M{x0},{yy} h{w}" stroke="#ddd"/>']
   for shift in [-8,-4,0,4,8]:
    xx=x0+(shift+8)/16*w
    out += [f'<text x="{xx-8}" y="{y0+h+20}">{shift}</text>']
   for qi,q in enumerate(curves):
    pts=' '.join(f'{x0+(v["shift"]+8)/16*w:.2f},{y0+h-h*v[f"{part}_RMSE_rad"]/ym:.2f}' for v in q['curve'])
    color=colors[qi%len(colors)]
    out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    out.append(f'<text x="{x0+qi*170}" y="{y0+h+40}" style="fill:{color}">{q["variant"]}</text>')
 out += ['<text x="30" y="557">120 Hz grid is the delivered training-label grid: six/eight commands are interpolated, not measured native ticks.</text>','</svg>']
 return '\n'.join(out)

def main():
 started=time.monotonic();O.mkdir(parents=True,exist_ok=True)
 ip=P/'abc_openloop_pair_v1/A_SEALED_INDEX20.json';mp=P/'AB_all20_metadata_v2/INPUTS.json'
 assert sha(ip)=='1d53492f888b71be38d2af398b272706a67ec9ec065c57d4327c019382a1d937'
 assert sha(mp)=='944249b28c68196865ad169549a798b1173c712fdca311eff6b9f17fc5011d1f'
 index=json.loads(ip.read_text());meta=json.loads(mp.read_text());epmeta={e['episode']:e for e in meta['episodes']}
 variants=['mem0_30k','ours_aligned_30k']; sums={}; episodes=[]; checked_refs=[]
 for variant in variants:
  refs={r['episode']:r['ACTIONS'] for r in index['episodes'] if r['variant']==variant}
  assert sorted(refs)==EPISODES
  for eid in EPISODES:
   e=epmeta[eid];ap=D/e['arrays']['file']; assert sha(ap)==e['arrays']['sha256']
   f=Path(refs[eid]['file']);assert sha(f)==refs[eid]['sha256']
   with np.load(ap,allow_pickle=False) as z:
    chunks=np.array(z['position_targets_120hz'],dtype=np.float32).reshape(-1,8,13)
    raw=np.array(z['raw_action'],dtype=np.float32);validsteps=np.array(z['valid_steps'],dtype=int)
    valid=~np.array(z['action_is_pad'],dtype=bool);q=np.array(z['qpos'],dtype=np.float32)
   assert np.allclose(chunks[valid,0],raw[valid],atol=1e-6,rtol=1e-6)
   targets=chunks[np.arange(len(chunks)),np.maximum(validsteps-1,0)]
   records=[json.loads(s) for s in f.open() if s.strip()]
   assert [r['frame'] for r in records]==list(range(len(records)))
   prediction=np.asarray([r['prediction_A_absolute_rad'][0] for r in records],dtype=np.float64)
   # Common query set across all 17 shifts, no endpoint clamping or selective masks.
   frames=np.arange(8,min(len(records),len(targets)-8),dtype=int)
   keep=np.ones(len(frames),dtype=bool)
   for shift in SHIFTS:keep &= valid[frames+shift] & (validsteps[frames+shift]==8)
   frames=frames[keep];assert len(frames)>0
   for r in records:
    i=r['frame'];assert np.array_equal(np.asarray(r['target_absolute_rad'][0],np.float32),targets[i])
    assert np.array_equal(np.asarray(r['q13_rad'],np.float32),q[i])
   groups=np.array([(r.get('operation_segment')or{}).get('label')or'unknown' for r in records])
   per=[]
   for grid in ['policy_15Hz_rows','converted_120Hz_control_ticks']:
    for group in ['all','approach','close','transport','unknown']:
     selected=frames if group=='all' else frames[groups[frames]==group]
     curve=[]
     for shift in SHIFTS:
      if grid=='policy_15Hz_rows':label=targets[selected+shift]
      else:
       indices=8*selected+7+shift
       label=chunks.reshape(-1,13)[indices]
      err=prediction[selected]-label
      item=new();add(item,err);curve.append({'shift':shift,**finish(item)})
      key=(variant,grid,group,shift)
      if key not in sums:sums[key]=new()
      add(sums[key],err)
     per.append(dict(grid=grid,group=group,curve=curve))
   episodes.append(dict(variant=variant,episode=eid,order=e['order'],predicted_frames=len(records),common_queries=len(frames),curves=per))
   checked_refs.append(dict(variant=variant,episode=eid,arrays=ref(ap),predictions=ref(f),all_first_targets_exact_interval_end=True))
   dump(O/'PROGRESS.json',dict(epoch=time.time(),closed_episodes=len(episodes),planned=40))
 rows=[]
 for variant in variants:
  for grid in ['policy_15Hz_rows','converted_120Hz_control_ticks']:
   for group in ['all','approach','close','transport','unknown']:
    curve=[dict(shift=s,**finish(sums[(variant,grid,group,s)])) for s in SHIFTS]
    minima={part:min((v for v in curve if v[f'{part}_RMSE_rad'] is not None),key=lambda x:x[f'{part}_RMSE_rad'])['shift'] if curve[0]['n'] else None for part in ['arm','hand','all']}
    rows.append(dict(variant=variant,grid=grid,group=group,curve=curve,minimum_shift=minima))
 result=dict(schema='task7_first_target_time_shift_audit.v1',stage='diagnostic',epoch=time.time(),CPU_only=True,NN_calls=0,GPU_jobs=0,
  fixed_episodes=EPISODES,variants=variants,query_scope='complete first subtask plus 30 subsequent frames; common interior query set for every shift',
  shift_sign='prediction at query f compared against label at f+shift; positive means later label',
  target_contract={'action':'absolute q13 radians','query_first_target':'chunk[current_row, valid_steps-1]','normal_full_chunk':'substep7 zero based, native endpoint R+8','raw_action':'substep0, R+1','seven_tick_difference':'interval-end minus interval-start =7 physical ticks; deliberately selected by actual training loader, not seven policy rows','image_tick':'121+8f','state_tick':'124+8f','image_state_lag_ticks':3,'no_unrecorded_training_120Hz_state_claim':True},
  caveat='A nonzero empirical minimum can reflect model temporal bias and smooth labels; it does not by itself prove deployed indexing differs from the loader. Native tick curve uses converted interpolated command labels, never unrecorded physical measurements.',
  rows=rows,episodes=episodes,input_refs=checked_refs,index=ref(ip),metadata=ref(mp),entry=ref(Path(__file__)),wall_seconds=time.monotonic()-started)
 dump(O/'RESULT.json',result);(O/'RMSE_SHIFT_CURVES.svg').write_text(svg(rows))
 csv=['variant,grid,group,shift,n,arm_RMSE_rad,hand_RMSE_rad,all_RMSE_rad']
 for row in rows:
  for v in row['curve']:csv.append(','.join(str(x) for x in [row['variant'],row['grid'],row['group'],v['shift'],v['n'],v['arm_RMSE_rad'],v['hand_RMSE_rad'],v['all_RMSE_rad']]))
 (O/'RMSE_SHIFT_CURVES.csv').write_text('\n'.join(csv)+'\n')
 print(json.dumps(dict(complete=True,wall_seconds=result['wall_seconds'],result=ref(O/'RESULT.json'),summaries=[dict(variant=x['variant'],grid=x['grid'],minimum_shift=x['minimum_shift'],zero=x['curve'][8]) for x in rows if x['group']=='all'])))

if __name__=='__main__':
 try:main()
 except Exception as e:
  O.mkdir(parents=True,exist_ok=True);dump(O/'ERROR.json',dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc()));raise
