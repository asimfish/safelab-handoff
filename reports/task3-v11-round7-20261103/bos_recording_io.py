"""BOS-safe recorder I/O: bounded RAM buffers, immutable final large writes.
No physics, control, rendering or oracle mutation. No disk spool outside BOS.
"""
from pathlib import Path
import io,hashlib,json
class DeferredText(io.StringIO):
 def __init__(self,path,limit=128<<20):super().__init__();self.path=Path(path);self.limit=limit
 def write(self,s):
  if self.tell()+len(s)>self.limit:raise MemoryError('bounded_raw_text_buffer_limit')
  return super().write(s)
 def close(self):
  if self.closed:return
  raw=self.getvalue().encode();self.path.write_bytes(raw)
  if hashlib.sha256(self.path.read_bytes()).digest()!=hashlib.sha256(raw).digest():raise IOError('BOS_raw_text_sha_mismatch')
  super().close()
class DeferredH5:
 def __init__(self,path,real_file):
  self.path=Path(path);self.buffer=io.BytesIO();self.file=real_file(self.buffer,'w');self.closed=False
 def __getattr__(self,k):return getattr(self.file,k)
 def close(self):
  if self.closed:return
  self.file.flush();self.file.close();raw=self.buffer.getvalue()
  if len(raw)>512<<20:raise MemoryError('bounded_particle_buffer_limit')
  self.path.write_bytes(raw)
  if hashlib.sha256(self.path.read_bytes()).digest()!=hashlib.sha256(raw).digest():raise IOError('BOS_particle_sha_mismatch')
  self.buffer.close();self.closed=True

def install(native,small_root):
 import h5py
 # Recorder construction occurs after the source module loads, before any record.
 original_initial=native.initial_gate
 def initial(owner,deadline):
  result=original_initial(owner,deadline)
  import whole_native_qualification as module
  old=module.Recorder.__init__
  def init(self,*args,**kw):
   real_open=Path.open;real_h5=h5py.File
   def scoped_open(path,mode='r',*a,**k):
    if mode=='w' and path.name in ('evaluator_trace_120hz.jsonl','native_controls_120hz.jsonl'):return DeferredText(path)
    return real_open(path,mode,*a,**k)
   def scoped_h5(path,*a,**k):
    if Path(path).name=='actual_particle_positions_120hz.h5':return DeferredH5(path,real_h5)
    return real_h5(path,*a,**k)
   Path.open=scoped_open;h5py.File=scoped_h5
   try:old(self,*args,**kw)
   finally:Path.open=real_open;h5py.File=real_h5
  module.Recorder.__init__=init
  return result
 native.initial_gate=initial
 original_dump=native.dump
 def dump(path,value):
  if Path(path).name=='EXPERT_HEARTBEAT.json':
   target=Path(small_root)/'EXPERT_HEARTBEAT.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(value));return
  return original_dump(path,value)
 native.dump=dump
