"""CPU native-target label shift check; uses cached predictions, not measured physics."""
from pathlib import Path
import hashlib,io,json,os
import numpy as np
import pyarrow.parquet as pq
S=Path('/project_a02012413/public/liyufeng/safelab_task10_new_variants_20261102/eval_v11_20261103');A=S/'inference_enhancements_20261106';EPS=list(range(10))+list(range(50,60))
root=Path('/projects/a02012413/buckets/zenith-a02012413/liyufeng/safelab_task10_new_variants_20261102/diagnostic_traininit_notopple_20261105/training20_inputs/adapted20/data/chunk-000')
key='action.joint_position_target_chunk_120hz';valid='action.chunk_120hz_valid_steps';labels={};valid_counts={};inputs=[]
for ep in EPS:
 p=root/f'episode_{ep:06d}.parquet';raw=p.read_bytes();inputs.append({'episode':ep,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});rows=pq.read_table(io.BytesIO(raw),columns=[key,valid]).to_pydict();chunks=[np.asarray(x,dtype=np.float32).reshape(-1,13)for x in rows[key]];assert all(0<len(c)<=8 for c in chunks),ep;labels[ep]=chunks;valid_counts[ep]=[int(np.asarray(v).reshape(-1)[0])for v in rows[valid]]
for method,folder in [('mem0_original','timing20_mem0_original'),('ours_aligned','timing20_ours_aligned_v3')]:
 p=A/folder/'PREDICTIONS.json';raw=p.read_bytes();probes=json.loads(raw);assert len(probes)==40 and {x['episode']for x in probes}==set(EPS);assert {x['frame']for x in probes}=={8,32}
 curves=[]
 for lag in range(-8,9):
  residuals=[]
  for probe in probes:
   ep=probe['episode'];frame=probe['frame'];row_offset,tick_in_row=divmod(7+lag,8);assert tick_in_row<valid_counts[ep][frame+row_offset];target=labels[ep][frame+row_offset][tick_in_row];prediction=np.asarray(probe.get('prediction_first',probe.get('prediction')))
   if prediction.ndim==2:prediction=prediction[0]
   assert prediction.shape==(13,) and np.isfinite(prediction).all();residuals.append(prediction-target)
  error=np.asarray(residuals);curves.append({'lag_native_target_ticks':lag,'lag_ms':lag/120*1000,'arm_RMSE_rad':float(np.sqrt(np.mean(error[:,:7]**2))),'hand_RMSE_rad':float(np.sqrt(np.mean(error[:,7:]**2)))})
 result={'method':method,'stage':'diagnostic','CPU_only':True,'episodes':EPS,'observation_frames':[8,32],'probe_count':40,'prediction_source':str(p),'prediction_source_sha256':hashlib.sha256(raw).hexdigest(),'reference':'native120Hz TARGET LABELS, not measured physics120 states','zero_convention':'same frame chunk[7], interval_end; lag-7 is raw action/first-of8; lag+1 is next row chunk[0]','curve':curves,'minimum':{part:min(curves,key=lambda x:x[part+'_RMSE_rad'])['lag_native_target_ticks']for part in ['arm','hand']},'input_parquets':inputs,'inference_or_executor_changed':False,'interpretation_limit':'RMSE-optimal shift can reflect model prediction bias; a global I/O timing bug requires corroborating training/deployment contract mismatch. No automatic action shift.'}
 (A/(method+'_NATIVE_TARGET_TICK_TIMING.json')).write_text(json.dumps(result,indent=2));print(json.dumps({'method':method,'minimum':result['minimum'],'zero':curves[8],'raw_first_of8':curves[1]}),flush=True)
os.environ['MPLCONFIGDIR']=str(A/'native_tick_timing_matplotlib_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
for method,label in [('mem0_original','Mem-0'),('ours_aligned','TTC aligned')]:
 d=json.loads((A/(method+'_NATIVE_TARGET_TICK_TIMING.json')).read_text())
 for ax,part in zip(axes,['arm','hand']):ax.plot([x['lag_native_target_ticks']for x in d['curve']],[x[part+'_RMSE_rad']for x in d['curve']],marker='.',label=label)
for ax,part in zip(axes,['Arm','Hand']):
 ax.axvline(0,color='black',ls='--',lw=1);ax.axvline(-7,color='grey',ls=':',lw=1);ax.set(xlabel='Native target-label shift (120 Hz ticks)',ylabel='RMSE (rad)',title=part+' / 20 episodes, 40 fixed probes');ax.legend();ax.grid(alpha=.2)
fig.savefig(A/'native_target_tick_timing.svg');plt.close(fig)
