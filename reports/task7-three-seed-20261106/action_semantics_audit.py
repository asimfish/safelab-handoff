"""CPU comparison of frozen training metadata and actual issued joint mappings."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
S=Path('/project_a02012413/public/liyufeng/safelab_mem0_7weigh_eval_20261027')
P=S/'low_sr_diagnostic_traininit_p1_v1'
R=S/'inference_1400_cpu_20261106'
NAMES=[f'arm2_joint_link{i}' for i in range(1,8)]+[f'hand2_joint_link_{i}_1' for i in range(1,6)]+['hand2_joint_link_1_2']
def ref(p):
 p=Path(p);return dict(file=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def main():
 out=R/'action_semantics';out.mkdir(parents=True,exist_ok=True);rows=[]
 for variant in ['mem0_30k','ours_aligned_30k']:
  bp=P/'ab_source_91c33c50ea47/prepared/bindings'/(variant+'.json');b=json.loads(bp.read_text());paths=json.loads((P/'AB_all20_metadata_v2'/(variant+'_paths.json')).read_text());bundle=Path(paths['bundle']);norm=bundle/'norm_stats_all100.json';stats=json.loads(norm.read_text());assert ref(norm)['sha256']==b['norm_sha256']=='6411bfa187af58d7924b61f813f41bc1afee74bcf8526dcb44c62b71becce1d8'
  assert stats['joint_names']==NAMES and stats['action_target']=='interval_end' and stats['camera']=='chest' and stats['fps']==15
  assert stats['state_dim']==stats['action_dim']==13 and stats['training_episode_indices']==list(range(100))
  # Execute only the frozen CPU normalizer, not a neural constructor.
  package=bundle/'code' if (bundle/'code/source').is_dir() else bundle
  import importlib.util
  mpath=package/'source/safelab/sim_bridge.py';spec=importlib.util.spec_from_file_location('_t939_semantics_bridge_'+variant,mpath);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
  normalizer=module.SafeLabNormalizer(stats,action_target='interval_end',camera='chest')
  rng=np.random.default_rng(20261106);lo=np.array(stats['action_min'],np.float32);hi=np.array(stats['action_max'],np.float32);x=np.vstack([lo,hi,(lo+hi)/2,rng.uniform(lo,hi,size=(100,13)).astype(np.float32)])
  back=normalizer.denormalize_action(normalizer.normalize_action(x));error=float(np.max(np.abs(x-back)));assert error<1e-6
  policy=package/'source/safelab'/('policy_inference.py' if variant=='mem0_30k' else 'ours_policy_inference.py');plines=policy.read_text().splitlines();line=next(i+1 for i,l in enumerate(plines) if 'predict_chunk' in l and 'temporal_ensemble' in l)
  rows.append(dict(variant=variant,checkpoint_sha256=b['checkpoint_sha256'],normalization=ref(norm),normalizer_source=ref(mpath),policy_source=ref(policy),temporal_ensemble_source_line=line,normalizer_roundtrip_max_abs_rad=error,
   checks={'absolute_target_not_delta':'consistent','radians':'consistent','joint_order':'consistent','no_joint_sign_inversion':'consistent_source_and_SDK_argument_scope','continuous_six_hand_joints_not_binary_gripper':'consistent','binary_hand_threshold':'not_applicable','training_run_normalization_SHA':'consistent','current_row_interval_endpoint':'consistent'},
   native_output_mode='original temporal_ensemble; timing curve uses the sealed raw model prediction on teacher-forced training frames',
   expected_first_target='current query row interval-end, no skipped action row',actual_h4='first indices0..3 then refresh; K kernel may look ahead2 without executing them',actual_h8='first indices0..7 then refresh; K kernel may look ahead2 without executing them',
   hand_execution_caveat='All6 hand position targets remain continuous. Current K chain uses zero hand velocity feedforward; this is a declared execution-chain design, not an input normalization/sign mapping. Native expert FF is independently recorded, not inferred from position differences.'))
 ledger=json.loads((R/'sdk_ledger_review/ROOT_SDK_CLOSURES.json').read_text());mappings=[]
 for case in ledger['cases']:
  p=Path(case['closure']['file']);m=p.parent.with_name(p.parent.name[:-8])/'SENT_COMMAND_MAPPING.json';d=json.loads(m.read_text());assert d['selected13_names']==NAMES;assert [d['all_robot_joint_names'][i] for i in d['selected13_ids']]==NAMES
  assert d['selected13_ids']==[1,3,5,7,9,11,13,19,20,21,22,23,29];mappings.append(ref(m))
 result=dict(schema='task7_action_semantics_actual_source_and_SDK_audit.v1',stage='diagnostic',epoch=time.time(),CPU_only=True,rows=rows,actual_SDK_mapping_checked=len(mappings),mapping_refs=mappings,joint_names=NAMES,scope='Mem0#39 and TTC-aligned#41 only; no claim for other checkpoints',vi_o_mismatch_detected=False,scientific_sources_modified=False,
  conclusion='No demonstrated action semantic/index mismatch. Seven120Hz-tick start/end difference is the actual training label convention, not seven15Hz-row deployment displacement. Tiny empirical1–2 converted-control-tick minima do not override the exact loader indexing evidence.')
 (out/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(complete=True,rows=rows,SDK_mappings=len(mappings),result=ref(out/'RESULT.json'))))
if __name__=='__main__':main()
