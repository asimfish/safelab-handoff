"""SafeLab strict-fdvel-v1: same frozen strict oracle, measured-pose FD velocities.

Generic fd_pair / iter_fd_rows are reusable by other tasks. rescore_stream is
T3-specific and retains its original strict thresholds, windows and ordering.
No simulator/model imports, PhysX fallback, nominal-dt substitution or writes.
"""
from pathlib import Path
import ast
import hashlib
import json
import math
import sys

SUPPORT = Path('/project_a02012413/public/liyufeng/safelab_mem0_five_seed_pro8_20261029/eval_v1/round7/r10_canonical_support/source/runtime')
ORACLE_SHA = '43d58adecd639cdcbc5ebbe71314503dbbebf14504fa24165452d4e4c9529721'
TIME_KEY = 'actual_physics_elapsed_s'

class UnknownTrace(ValueError):
    pass

def vector(value, size):
    try:
        if len(value) != size or any(isinstance(x, bool) for x in value):
            raise UnknownTrace('invalid_pose_shape')
        result = [float(x) for x in value]
        if not all(math.isfinite(x) for x in result):
            raise UnknownTrace('nonfinite_pose')
        return result
    except UnknownTrace:
        raise
    except (ValueError, TypeError, OverflowError) as exc:
        raise UnknownTrace('missing_or_invalid_pose') from exc

def fd_pair(previous, current, *, time_key=TIME_KEY):
    """Return per-object linear/angular world velocities; dt is recorded time."""
    try:
        if not isinstance(previous,dict) or not isinstance(current,dict):
            raise UnknownTrace('row_is_not_an_object')
        if not isinstance(previous.get('objects'),dict) or not isinstance(current.get('objects'),dict):
            raise UnknownTrace('missing_objects_map')
        if not all(isinstance(x,dict)for x in list(previous['objects'].values())+list(current['objects'].values())):
            raise UnknownTrace('invalid_object_pose_record')
        t0, t1 = previous[time_key], current[time_key]
        if isinstance(t0, bool) or isinstance(t1, bool):
            raise UnknownTrace('invalid_timestamp')
        dt = float(t1)-float(t0)
        if not math.isfinite(dt) or dt <= 0:
            raise UnknownTrace('nonpositive_or_nonfinite_dt')
        if type(previous['tick']) is not int or type(current['tick']) is not int or current['tick'] != previous['tick']+1:
            raise UnknownTrace('nonadjacent_physical_tick')
        if 'native_tick' in previous or 'native_tick' in current:
            if type(previous['native_tick']) is not int or type(current['native_tick']) is not int or current['native_tick'] != previous['native_tick']+1:
                raise UnknownTrace('nonadjacent_native_tick')
        if set(previous['objects']) != set(current['objects']) or not current['objects']:
            raise UnknownTrace('object_set_changed_or_empty')
        result = {}
        for key, obj in current['objects'].items():
            old = previous['objects'][key]
            p0, p1 = vector(old['link_position_world_m'],3), vector(obj['link_position_world_m'],3)
            q0, q1 = vector(old['quaternion_world_wxyz'],4), vector(obj['quaternion_world_wxyz'],4)
            n0, n1 = math.sqrt(sum(x*x for x in q0)), math.sqrt(sum(x*x for x in q1))
            if not math.isfinite(n0) or not math.isfinite(n1) or n0 <= 1e-12 or n1 <= 1e-12:
                raise UnknownTrace('zero_quaternion')
            w0,x0,y0,z0 = [x/n0 for x in q0]
            w1,x1,y1,z1 = [x/n1 for x in q1]
            # q_current * inverse(q_previous), world-frame relative rotation.
            w = w1*w0+x1*x0+y1*y0+z1*z0
            xyz = [-w1*x0+x1*w0-y1*z0+z1*y0,
                   -w1*y0+x1*z0+y1*w0-z1*x0,
                   -w1*z0-x1*y0+y1*x0+z1*w0]
            if w < 0:
                w, xyz = -w, [-x for x in xyz]
            n = math.sqrt(sum(x*x for x in xyz))
            theta = 2*math.atan2(n,w)
            angular = [x*theta/(n*dt) for x in xyz] if n else [0.,0.,0.]
            linear = [(b-a)/dt for a,b in zip(p0,p1)]
            if not all(math.isfinite(x) for x in linear+angular):
                raise UnknownTrace('nonfinite_FD_velocity')
            result[key] = {'linear_velocity_m_s':linear,'angular_velocity_rad_s':angular}
        return result
    except KeyError as exc:
        raise UnknownTrace('missing_adjacent_pose_or_clock') from exc
    except UnknownTrace:
        raise
    except (ValueError,TypeError, OverflowError) as exc:
        raise UnknownTrace('invalid_adjacent_pose_or_clock') from exc

def with_velocities(row, values):
    result = dict(row)
    result['objects'] = {k:dict(v,**values[k]) for k,v in row['objects'].items()}
    return result

def iter_fd_rows(rows, *, time_key=TIME_KEY):
    iterator = iter(rows)
    try:
        previous, current = next(iterator), next(iterator)
    except StopIteration as exc:
        raise UnknownTrace('two_adjacent_physical_samples_required') from exc
    velocities = fd_pair(previous,current,time_key=time_key)
    yield with_velocities(previous,velocities)  # First tick: forward difference.
    yield with_velocities(current,velocities)
    previous = current
    for current in iterator:
        yield with_velocities(current,fd_pair(previous,current,time_key=time_key))
        previous = current

def compile_strict(support=SUPPORT):
    import numpy as np
    support=Path(support)
    source=support/'audit_whole_t3_stream_liveness_v11.py'
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORACLE_SHA:
        raise ValueError('frozen_strict_oracle_SHA_mismatch')
    names={'require','norm','angle','released','OrderedPhysics','contacts'}
    tree=ast.parse(raw.decode())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    if {n.name for n in nodes}!=names:
        raise ValueError('incomplete_strict_oracle_AST')
    sys.path.insert(0,str(support))
    from native_clock_contract_v60 import bind_initial_row,validate_recorded
    ns={'np':np,'math':math,'bind_initial_row':bind_initial_row,'validate_recorded':validate_recorded}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(source),'exec'),ns)
    return ns

def rescore_stream(stream, *, expected_rows=None, expected_sha256=None, support=SUPPORT):
    """Consume original binary JSONL (local or authenticated SDK response stream)."""
    ns=compile_strict(support)
    sha=hashlib.sha256();count=0;raw_count=0;rec=None;physical_error=None;input_error=None
    def rows():
        nonlocal raw_count
        buf=b''
        while True:
            block=stream.read(1<<20)
            if not block:break
            sha.update(block);buf+=block
            parts=buf.split(b'\n');buf=parts.pop()
            for raw in parts:
                raw_count+=1
                yield json.loads(raw)
        if buf:
            raw_count+=1
            yield json.loads(buf)
    try:
        for row in iter_fd_rows(rows()):
            count+=1
            if physical_error is not None:continue
            try:
                if rec is None:rec=ns['OrderedPhysics'](row)
                ns['contacts'](row);rec.consume(row)
            except (KeyError,TypeError,IndexError) as exc:
                raise UnknownTrace('strict_required_field_missing_or_invalid') from exc
            except ValueError as exc:
                physical_error=str(exc)
        if expected_rows is not None and count!=expected_rows:
            raise UnknownTrace('trace_row_count_mismatch')
        if expected_sha256 is not None and sha.hexdigest()!=expected_sha256:
            raise UnknownTrace('source_trace_SHA_mismatch')
    except (UnknownTrace,json.JSONDecodeError,UnicodeDecodeError) as exc:
        input_error=str(exc)
    return {'stage':'diagnostic','protocol_version':'SafeLab-Eval-v1','oracle_version':'strict-fdvel-v1',
            'unknown':input_error is not None,'unknown_reason':input_error,
            'success':bool(rec and rec.phase==3 and physical_error is None and input_error is None),
            'physical_phase':(rec.phase if rec else 0) if input_error is None else None,
            'phase_times':rec.times if rec and input_error is None else [],
            'error':physical_error,'trace_sha256':sha.hexdigest(),'trace_sha_complete':input_error is None,'trace_rows':count,'raw_rows_parsed':raw_count,
            'oracle_source_sha256':ORACLE_SHA,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'time_key':TIME_KEY,'velocity_source':'adjacent actual120Hz pose / actual elapsed time',
            'first_tick':'forward_difference','other_strict_logic_unchanged':True}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('trace');ap.add_argument('--expected-rows',type=int);ap.add_argument('--expected-sha256');ap.add_argument('--support',default=str(SUPPORT));ap.add_argument('--output');a=ap.parse_args()
    with Path(a.trace).open('rb')as f:result=rescore_stream(f,expected_rows=a.expected_rows,expected_sha256=a.expected_sha256,support=a.support)
    text=json.dumps(result,indent=2)
    if a.output:Path(a.output).write_text(text+'\n')
    print(text)
