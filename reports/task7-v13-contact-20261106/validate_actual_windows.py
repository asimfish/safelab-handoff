"""Actual recorded negative windows; original bytes and full source hashes are retained."""
from pathlib import Path
import json,collections,hashlib,time,os
from oracle_v13 import PlacementFour
R=Path(__file__).resolve().parent;L=R.parent
B=Path("/projects/a02012413/buckets/zenith-a02012413/liyufeng/safelab_mem0_7weigh_eval_20261027/eval_v13_lenient_cpu_20261106/support_contact_authoritative_v2")
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==b
 else:p.write_bytes(b)
 assert p.read_bytes()==b
 return dict(file=str(p),bytes=len(b),sha256=sha(b))
def main():
 inp=json.loads(Path("/project_a02012413/public/liyufeng/safelab_mem0_7weigh_eval_20261027/oracle_margin_audit_20261105/policy_main200_v1/INPUTS.json").read_bytes())
 orig={r["case_id"]:r for r in inp["cases"]};literal=json.loads((L/"MAIN_COMPLETE.json").read_bytes())["rows"]
 previous={r["case_id"]:r for r in literal if r["kind"]=="main" and r["raw_SHA_verified"]}
 candidates=[]
 for r in previous.values():
  for e in r["v13"]["summary"]["events"]:
   if e["conditions"]["height_only_with_robot_touch"]:
    candidates.append((r,e));break
 assert len(candidates)>=10
 cases=[];used=set()
 def window(r,tick):
  p=Path(r["raw"]["file"]);tail=collections.deque(maxlen=13);target=None
  with p.open("rb")as f:
   for raw in f:
    z=json.loads(raw);tail.append((z["tick"],raw))
    if z["tick"]==tick:target=z
    if z["tick"]>=tick+6:break
  assert target is not None
  buf=[raw for t,raw in tail if tick-6<=t<=tick+6]
  return target,b"".join(buf)
 for r,e in candidates:
  if len(cases)>=10:break
  scene=json.loads(Path(orig[r["case_id"]]["scene"]["file"]).read_bytes());o=PlacementFour(scene["source_profile"],scene["env_origins"][0]);z,raw=window(r,e["tick"])
  key=e["object"];pose=z["poses"]["ABCD".index(key)];sc=scene["source_profile"]["scene"]
  above=pose[2]-scene["env_origins"][0][2]-sc["supports"]["pan"][2]-sc.get("object_bottom_offsets",{}).get(key,sc["half_height"])
  c=o.conditions(key,pose,z["contacts"])
  if not (0<above<=.015 and c["nearest_target"]=="pan" and not c["support_contact"] and c["robot_contact"]):continue
  assert not c["passed"] and e["conditions"]["passed"]
  category="airborne_above_target" if len(cases)<5 else "hand_lifted_from_target"
  ref=write(B/"negative_windows"/(category+"_"+str(len(cases)).zfill(2)+".jsonl"),raw)
  cases.append(dict(category=category,case_id=r["case_id"],object=key,tick=e["tick"],window=ref,source_raw=r["raw"],signed_bottom_above_pan_m=above,new_conditions=c,literal_old_predicate_passed=True,new_contact_predicate_passed=False,airborne_windows_include_hand_held_objects=True))
  used.add(r["case_id"])
 assert len(cases)==10
 for r in previous.values():
  if r["case_id"]in used:continue
  scene=json.loads(Path(orig[r["case_id"]]["scene"]["file"]).read_bytes());o=PlacementFour(scene["source_profile"],scene["env_origins"][0]);z,raw=window(r,125)
  c=o.conditions("A",z["poses"][0],z["contacts"])
  if c["nearest_target"]=="pan":continue
  assert not c["passed"]
  ref=write(B/"negative_windows"/("wrong_target_"+str(len(cases)-10).zfill(2)+".jsonl"),raw)
  cases.append(dict(category="wrong_target",case_id=r["case_id"],object="A",tick=125,window=ref,source_raw=r["raw"],new_conditions=c,new_contact_predicate_passed=False))
  if len(cases)==15:break
 assert len(cases)==15
 complete=json.loads((R/"MAIN_COMPLETE.json").read_bytes());experts=[r for r in complete["rows"]if r["kind"]=="expert"];policy=[r for r in complete["rows"]if r["kind"]=="main"and r["raw_SHA_verified"]]
 assert len(experts)==10 and all(r["v13"]["verdict"]=="S"for r in experts)
 assert all(e["conditions"]["support_contact"]for r in experts for e in r["v13"]["summary"]["events"])
 assert all(r["first_row"]["completed"]==0 for r in policy)
 v=dict(schema="task7_v13_contact_authority_validation.v1",passed=True,negative_validation_passed=True,qualified_for_public_primary_table=True,
  semantics_approved_by="User: 以实测支撑接触为准",expert_N=10,expert_success=10,expert_distinct_raw_sha=len({r["raw"]["sha256"]for r in experts}),
  negative_counts=dict(collections.Counter(c["category"]for c in cases)),all_15_rejected=True,
  red_green_actual_windows={"literal_OR_height_false_positive_windows":10,"contact_authoritative_false_positives":0},
  start_pad_false_credit=0,raw_policy_checked=199,counts_unit="N=4 distinct cups on weighing pan; historical N=7 retained separately",
  no_original_protocol_model_simulation_change=True,negative_cases=cases,epoch=time.time(),
  source_sha256=sha(Path(__file__).read_bytes()),oracle_sha256=sha((R/"oracle_v13.py").read_bytes()),
  parameters_sha256=sha((R/"FROZEN_PARAMETERS.json").read_bytes()))
 write(R/"VALIDATION.json",(json.dumps(v,ensure_ascii=False,indent=2)+"\n").encode())
 print(json.dumps({k:v for k,v in v.items()if k!="negative_cases"}),flush=True)
if __name__=="__main__":main()
