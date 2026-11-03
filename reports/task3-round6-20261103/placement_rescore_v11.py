"""T-1035 offline placement-v1.1 implementation; pending expert/video admission.

Does not mutate traces, the running strict oracle, physics or official scores.
Keeps all non-placement safety/order/liquid/carry constraints from frozen v1.
"""
from pathlib import Path
import ast, hashlib, json, math, sys
import numpy as np
SUPPORT=Path('/public_fast_storage/liyufeng/safelab_mem0_v13_eval_20261024/environment_support/source/runtime')
ORACLE=SUPPORT/'audit_whole_t3_stream_liveness_v11.py'
ORACLE_SHA='43d58adecd639cdcbc5ebbe71314503dbbebf14504fa24165452d4e4c9529721'
PARAMETERS={'xy_tolerance_m':.020,'upright_cos_min':.97,'rest_height_tolerance_m':.005,'debounce_seconds':.25,'velocity_threshold':None,'retain_nonplacement_constraints':True,'final_placement_check':'recorded_episode_end','admission_status':'pending_expert_and_negative_video_checks'}
def placement(row,key,pad):
    obj=row['objects'][key];target=row['supports'][pad]['center_world_m']
    return (np.linalg.norm(np.asarray(obj['link_position_world_m'])[:2]-target[:2])<=PARAMETERS['xy_tolerance_m']
        and math.cos(math.radians(obj['tilt_deg']))>=PARAMETERS['upright_cos_min']
        and obj['robot_contact_points']==0
        and (obj['support_contact_points'].get(pad,0)>0 or abs(obj['bottom_world_z_m']-target[2])<=PARAMETERS['rest_height_tolerance_m']))
def compile_oracle():
    raw=ORACLE.read_bytes();assert hashlib.sha256(raw).hexdigest()==ORACLE_SHA
    src=raw.decode();old="else:condition=released(row,'A','rack_S1')and counts['B']>=.95*self.total;duration=3"
    assert src.count(old)==1;src=src.replace(old,old.replace('duration=3','duration=.25'))
    old="require(released(row,'A','rack_S1')and released(row,'B','rack_S2'),'post_completion_preservation_failed');return"
    assert src.count(old)==1;src=src.replace(old,'return # placement retention is checked at recorded episode end')
    tree=ast.parse(src);names={'require','norm','angle','released','OrderedPhysics','contacts'}
    nodes=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))and x.name in names]
    for node in nodes:
        if isinstance(node,ast.FunctionDef)and node.name=='released':
            node.body=ast.parse('return placement(row,key,pad)').body
    tree=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]));sys.path.insert(0,str(SUPPORT))
    from native_clock_contract_v60 import bind_initial_row,validate_recorded
    ns={'np':np,'math':math,'placement':placement,'bind_initial_row':bind_initial_row,'validate_recorded':validate_recorded}
    exec(compile(tree,str(ORACLE),'exec'),ns);return ns

def rescore(trace,expected_rows=None):
    ns=compile_oracle();rec=None;error=None;last=None;previous=None;count=0;sha=hashlib.sha256()
    with Path(trace).open('rb')as f:
        for raw in f:
            sha.update(raw);row=json.loads(raw);count+=1
            if previous is not None and row['tick']!=previous+1:raise ValueError('trace_tick_gap')
            previous=row['tick'];last=row
            if error is not None:continue
            try:
                if rec is None:rec=ns['OrderedPhysics'](row)
                ns['contacts'](row);rec.consume(row)
            except Exception as exc:error=str(exc)
    if expected_rows is not None and count!=expected_rows:raise ValueError('trace_row_count_mismatch')
    final_placed=bool(last and placement(last,'A','rack_S1')and placement(last,'B','rack_S2'))
    if rec and rec.phase==3 and error is None and not final_placed:error='final_placement_not_retained'
    return {'stage':'diagnostic','protocol_version':'SafeLab-Eval-v1.1','oracle_version':'placement-v1.1','admission_status':PARAMETERS['admission_status'],'parameters':PARAMETERS,'oracle_source_sha256':ORACLE_SHA,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'trace_sha256':sha.hexdigest(),'trace_rows':count,'success':bool(rec and rec.phase==3 and error is None),'physical_phase':rec.phase if rec else None,'phase_times':rec.times if rec else [],'final_placed':final_placed,'error':error,'recorded_prefix_only':True}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('--expected-rows',type=int);p.add_argument('--output');a=p.parse_args();v=rescore(a.trace,a.expected_rows);s=json.dumps(v,indent=2)
    if a.output:Path(a.output).write_text(s+'\n')
    print(s)
