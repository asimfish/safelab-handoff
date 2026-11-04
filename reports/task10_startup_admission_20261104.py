"""Bounded operational GPU admission queries; no model or physics behavior."""
import subprocess,threading,time
_locks={i:threading.Lock() for i in range(8)}
def free_memory(gpu,runner=subprocess.check_output,sleeper=time.sleep,on_retry=None):
 with _locks[gpu]:
  for attempt in range(3):
   try:
    value=int(runner(['nvidia-smi','--id='+str(gpu),'--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True,timeout=60).strip())
    if value<0:raise ValueError('negative GPU free memory')
    return value
   except subprocess.TimeoutExpired:
    if on_retry:on_retry(dict(gpu=gpu,attempt=attempt+1,epoch=time.time(),error='nvidia-smi timeout',timeout_seconds=60))
    if attempt==2:raise
    sleeper(2)


class StartupAdmission:
    """Bound native startup concurrency and reserve headroom for unresolved peers."""
    def __init__(self,gpus,min_free_mib=32768,reader=None,on_retry=None,max_initializing=1,per_pending_mib=8192):
        if max_initializing not in (1,2) or min_free_mib<=0 or per_pending_mib<0:raise ValueError('invalid startup capacity')
        self.slots={g:threading.BoundedSemaphore(max_initializing) for g in range(gpus)}
        self.gates={g:threading.Lock() for g in range(gpus)}
        self.pending={g:0 for g in range(gpus)}
        self.minimum=min_free_mib;self.reader=reader;self.on_retry=on_retry;self.per_pending=per_pending_mib
    def acquire(self,gpu,timeout=3):
        slot=self.slots[gpu]
        if not slot.acquire(timeout=timeout):return False
        retained=False
        try:
            with self.gates[gpu]:
                available=self.reader(gpu) if self.reader is not None else free_memory(gpu,on_retry=self.on_retry)
                retained=available>self.minimum+self.per_pending*self.pending[gpu]
                if retained:self.pending[gpu]+=1
            return retained
        finally:
            if not retained:slot.release()
    def release(self,gpu):
        with self.gates[gpu]:
            if self.pending[gpu]<=0:raise RuntimeError('startup reservation released twice')
            self.pending[gpu]-=1;self.slots[gpu].release()
