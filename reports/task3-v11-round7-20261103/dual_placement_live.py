"""Live placement primary plus unchanged strict-v1 shadow; no controls/physics writes."""
import json
from pathlib import Path
from placement_rescore_v11 import compile_oracle,placement
class DualOrdered:
 def __init__(self,first,strict_class):
  self.primary=compile_oracle()['OrderedPhysics'](first);self.last=first;self.error=None;self.strict_error=None;self.strict=None
  try:self.strict=strict_class(first)
  except Exception as exc:self.strict_error=str(exc)
 def __getattr__(self,name):return getattr(self.primary,name)
 def consume(self,row):
  self.last=row
  if self.strict_error is None:
   try:self.strict.consume(row)
   except Exception as exc:self.strict_error=str(exc)
  try:self.primary.consume(row)
  except Exception as exc:self.error=str(exc);raise
 def complete(self):return bool(self.primary.phase==3 and self.error is None and placement(self.last,'A','rack_S1')and placement(self.last,'B','rack_S2'))
 def strict_complete(self):return self.strict is not None and self.strict.phase==3 and self.strict_error is None
 def summary(self):return {'protocol_version':'SafeLab-Eval-v1.1','oracle_version':'placement-v1.1','success':self.complete(),'physical_phase':self.primary.phase,'phase_times':self.primary.times,'primary_error':self.error,'strict_v1':{'success':self.strict_complete(),'physical_phase':self.strict.phase if self.strict else None,'error':self.strict_error},'no_controls_or_physics_modified':True}
def install(native):
 original=native.replay_expert
 def wrapped(*args,**kwargs):
  import whole_native_qualification as w
  base=w.Recorder
  class Recorder(base):
   def __init__(self,*a,**k):
    super().__init__(*a,**k);strict_class=self.OrderedPhysics;self.OrderedPhysics=lambda first:DualOrdered(first,strict_class)
   def close(self):
    try:super().close()
    finally:
     if self.ordered is not None:(self.out/'DUAL_ORACLE.json').write_text(json.dumps(self.ordered.summary(),indent=2))
  w.Recorder=Recorder
  try:return original(*args,**kwargs)
  finally:w.Recorder=base
 native.replay_expert=wrapped
