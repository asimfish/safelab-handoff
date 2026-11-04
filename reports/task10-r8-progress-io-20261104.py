"""Best-effort shared progress mirror: simulation submit never performs storage I/O."""
import json,os,threading,time
from pathlib import Path
def atomic_json_bytes(path,payload):
 path=Path(path);tmp=path.with_name(path.name+f'.{os.getpid()}.{threading.get_ident()}.{time.monotonic_ns()}.pending')
 with tmp.open('xb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
 tmp.replace(path)
class ProgressMirror:
 def __init__(self,path,writer=atomic_json_bytes,retry_s=1.0):
  self.path=Path(path);self.writer=writer;self.retry_s=retry_s;self.cv=threading.Condition();self.payload=None;self.version=0;self.acked=0;self.errors=0;self.last_errno=None;self.stopping=False;self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
 def submit(self,value):
  payload=json.dumps(value,allow_nan=False,separators=(',',':')).encode()
  with self.cv:
   if self.stopping:raise RuntimeError('progress mirror already closed')
   self.version+=1;self.payload=payload;self.cv.notify_all();return self.version
 def _run(self):
  while True:
   with self.cv:
    self.cv.wait_for(lambda:self.stopping or self.version>self.acked)
    if self.stopping:return
    version=self.version;payload=self.payload
   try:self.writer(self.path,payload)
   except OSError as error:
    with self.cv:self.errors+=1;self.last_errno=error.errno;self.cv.wait(timeout=self.retry_s)
   else:
    with self.cv:self.acked=max(self.acked,version);self.last_errno=None;self.cv.notify_all()
 def flush(self,timeout):
  end=time.monotonic()+timeout
  with self.cv:
   while self.acked<self.version:
    remaining=end-time.monotonic()
    if remaining<=0:return False
    self.cv.wait(timeout=remaining)
   return True
 def close(self,timeout=1):
  complete=self.flush(timeout)
  with self.cv:self.stopping=True;self.cv.notify_all()
  self.thread.join(timeout=timeout);return complete

import json,os,time,threading
from pathlib import Path

class LocalProgress:
 def __init__(self,local_path,shared_path,writer=atomic_json_bytes,retry_s=2):
  self.local=Path(local_path);assert str(self.local).startswith('/tmp/safelab_task10_r8_')
  self.local.parent.mkdir(parents=True,exist_ok=True);self.mirror=ProgressMirror(shared_path,writer=writer,retry_s=retry_s)
 def write(self,value):
  with self.mirror.cv:status={'archive_pending':self.mirror.acked<self.mirror.version,'mirror_error_count':self.mirror.errors,'mirror_last_errno':self.mirror.last_errno}
  payload={**value,'progress_mirror':status}
  atomic_json_bytes(self.local,json.dumps(payload,allow_nan=False,separators=(',',':')).encode())
  self.mirror.submit(payload)
  return payload
 def close(self,timeout=1):return self.mirror.close(timeout)
