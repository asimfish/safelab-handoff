from pathlib import Path
import json,collections,math,random,hashlib,time
ROOT=Path(__file__).resolve().parent
PROTOS=("strict","v1.1","v1.2-relaxed","v1.3-lenient")
def save(p,a):
 b=(json.dumps(a,ensure_ascii=False,allow_nan=False,indent=2)+"\n").encode();tmp=p.with_name(p.name+".pending");tmp.write_bytes(b);tmp.replace(p)
 return dict(file=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def quant(a,p):
 a=sorted(a);x=(len(a)-1)*p;i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def ci(a):return [quant(a,.025),quant(a,.975)] if a else None
def boot(strata):
 a=[v for x in strata.values()for v in x]
 if not a:return None
 rng=random.Random(20261106);vals=[]
 for _ in range(10000):
  sample=[v for x in strata.values()for v in rng.choices(x,k=len(x))]
  vals.append(sum(sample)/len(sample))
 return ci(vals)
def wilson(s,n):
 z=1.959963984540054;d=1+z*z/n;c=(s/n+z*z/(2*n))/d;t=z*((s/n)*(1-s/n)/n+z*z/(4*n*n))**.5/d
 return [max(0,c-t),min(1,c+t)]
def get(r,p):
 n=4 if p=="v1.3-lenient"else 7
 if r is None or not r.get("raw_SHA_verified"):return dict(verdict="U",phase=None,N=n)
 q=r["v13"] if p=="v1.3-lenient"else r["historical_protocols"][p]
 return {**q,"N":n}
def summarize(rows,p):
 n=4 if p=="v1.3-lenient"else 7
 count=collections.Counter();hist=collections.Counter();sides={o:dict(N=50,S=0,F=0,U=0)for o in ("1234","4321")};strata={o:[]for o in sides};per={str(k):collections.Counter(S=0,F=0,U=0)for k in range(1,n+1)}
 for order,r in rows:
  q=get(r,p);v=q["verdict"];count[v]+=1;sides[order][v]+=1
  phase=q.get("phase")
  if v!="U" and phase is not None:hist[phase]+=1;strata[order].append(phase)
  for k,z in per.items():
   kk=int(k);code="S"if phase is not None and phase>=kk else"F"if v=="F"else"U";z[code]+=1
 s=count["S"];u=count["U"];valid=sum(hist.values())
 return dict(N=100,success=s,failure=count["F"],unknown=u,total_stages=n,unit="distinct cups on pan"if n==4 else"ordered subtasks",
  success_rate=s/100 if not u else None,confirmed_success_fraction=s/100,success_identification_bounds=[s/100,(s+u)/100],
  Wilson95_confirmed_full_denominator=wilson(s,100),mean_phase=sum(k*v for k,v in hist.items())/valid if valid else None,
  mean_phase_valid_n=valid,mean_phase_bootstrap95=boot(strata),phase_hist_valid=dict(sorted(hist.items())),
  half_task_k=math.ceil(n/2),half_task={**dict(per[str(math.ceil(n/2))]),"confirmed_fraction":per[str(math.ceil(n/2))]["S"]/100},
  SR_at_k={k:{**dict(z),"confirmed_fraction":z["S"]/100,"identification_bounds":[z["S"]/100,(z["S"]+z["U"])/100],"Wilson95_confirmed_fullN":wilson(z["S"],100)}for k,z in per.items()},left_right=sides)
def main():
 start=time.time();main=json.loads((ROOT/"MAIN_COMPLETE.json").read_bytes())["rows"];pi=json.loads((ROOT/"PI05_COMPLETE.json").read_bytes())["rows"]
 groups={}
 for variant in ("mem0_30k","ours_aligned_30k"):
  rs=[r for r in main if r["kind"]=="main"and r["variant"]==variant]
  assert len(rs)==100;groups[variant+"_h8"]=[(r["order"],r)for r in rs]
 pi_by={r["case_id"]:r for r in pi}
 for h in (4,8):
  rows=[]
  for o in ("1234","4321"):
   for i in range(50):
    cid=f"pi05_seven40k_stageA_h{h}_v180_o{o}_r{i:03d}";rows.append((o,pi_by.get(cid)))
  groups["pi05_40k_h"+str(h)]=rows
 summary={name:{p:summarize(rows,p)for p in PROTOS}for name,rows in groups.items()}
 paired={}
 mem={r["seed"]:r for o,r in groups["mem0_30k_h8"]};ttc={r["seed"]:r for o,r in groups["ours_aligned_30k_h8"]}
 for p in PROTOS:
  phase={o:[]for o in ("1234","4321")};success={o:[]for o in phase};bounds=[0,0]
  for seed in sorted(mem):
   a=get(mem[seed],p);b=get(ttc[seed],p);order=mem[seed]["order"]
   amin=1 if a["verdict"]=="S"else 0;amax=1 if a["verdict"]in("S","U")else 0;bmin=1 if b["verdict"]=="S"else 0;bmax=1 if b["verdict"]in("S","U")else 0
   bounds[0]+=bmin-amax;bounds[1]+=bmax-amin
   if a["verdict"]!="U"and b["verdict"]!="U":
    phase[order].append(b["phase"]-a["phase"]);success[order].append(int(b["verdict"]=="S")-int(a["verdict"]=="S"))
  d=[v for a in phase.values()for v in a];s=[v for a in success.values()for v in a]
  paired[p]=dict(known_pairs=len(d),unknown_pairs=100-len(d),mean_phase_difference=sum(d)/len(d)if d else None,mean_phase_difference_bootstrap95=boot(phase),
   success_difference_known_pairs=sum(s)/len(s)if s else None,success_difference_bootstrap95_known_pairs=boot(success),
   full100_success_difference_identification_bounds=[x/100 for x in bounds])
 expert=[r for r in main if r["kind"]=="expert"];counterexamples=[]
 for r in expert+[r for r in main if r["kind"]=="main"]:
  for e in r.get("v13",{}).get("summary",{}).get("events",[]):
   c=e["conditions"]
   if c["height_only_with_robot_touch"]:
    counterexamples.append(dict(case_id=r["case_id"],kind=r["kind"],object=e["object"],tick=e["tick"],conditions=c,source_raw=r["raw"]))
    break
  if len(counterexamples)>=5:break
 validation=json.loads((ROOT/"VALIDATION.json").read_bytes())
 assert validation["passed"] and validation["negative_validation_passed"]

 report=dict(schema="task7_four_protocol_first_draft.v1",protocol_version="SafeLab-Eval-v1.3-lenient",stage="diagnostic",
  status="CPU complete; v1.3 measured target-support contact validated; explicit user clarification",mean_unit_changed_from7to4=True,strict_v11_v12_original_rows_unchanged=True,
  groups=summary,paired_TTC_minus_Mem0=paired,validation=validation,
  source_files={n:{"sha256":hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),"bytes":(ROOT/n).stat().st_size}for n in ("oracle_v13.py","FROZEN_PARAMETERS.json","MAIN_COMPLETE.json","PI05_COMPLETE.json")},
  CPU_raw_valid=385,planned_policy_cases=400,raw_unknown=15,bootstrap={"replicates":10000,"seed":20261106,"stratified_by":"1234/4321 known valid pairs; unknown stays in full planned denominator; never phase0"},
  MemoryVLA={"status":"No registered task7 raw manifest in this frozen main/Pi05 input inventory; not inferred from other tasks"},
  elapsed_seconds=time.time()-start)
 ref=save(ROOT/"FIRST_FOUR_PROTOCOL_TABLE.json",report)
 lines=["Validated CPU first version: v1.3 follows the explicit user clarification that measured target-support contact is authoritative. Historical protocol rows are preserved.","",
 "|Method|Protocol|S / 100|Unknown|Half-task confirmed /100|Mean completed (known n)|","|---|---|---:|---:|---:|---:|"]
 for name,g in summary.items():
  for p,z in g.items():lines.append(f"|{name}|{p}|{z['success']}|{z['unknown']}|{z['half_task']['S']}|{z['mean_phase']} (n={z['mean_phase_valid_n']}, N={z['total_stages']})|")
 lines+=["","v1.3 N=4 distinct cups each on the weighing pan. Historical protocols N=7 ordered subtasks. Initial pads receive no credit.","",
 "Measured-support validation: 10/10 expert paths passed (3 unique raw traces); all 15 real negative windows rejected. Height-only suspended cases are rejected even inside the nominal 15mm band. Same parameters for all methods. Literal OR-height draft retained separately and not published as accepted.",
 "No new simulator, model, control or original strict/v1.1/v1.2 change. V1.3 counts four distinct cups; original admission and execution-chain limitations remain explicit.","",
 "Full SR@k, Wilson intervals, paired/bootstrap intervals and left/right splits are in FIRST_FOUR_PROTOCOL_TABLE.json."]
 save(ROOT/"FIRST_REPORT.md","\n".join(lines)) if False else None
 text="\n".join(lines)+"\n";(ROOT/"FIRST_REPORT.md").write_text(text)
 print(json.dumps({"report":ref,"table":{name:{p:{k:q[k]for k in ("success","unknown","mean_phase","half_task")}for p,q in g.items()}for name,g in summary.items()},"paired_v13":paired["v1.3-lenient"],"validation":{k:v for k,v in validation.items()if k!="first_five_real_counterexample_candidates"}}),flush=True)
if __name__=="__main__":main()
