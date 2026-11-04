from pathlib import Path
import importlib.util,json,threading,time
R=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('startup',R/'task10_startup_admission_20261104.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 checks=[];free=[40000];a=m.StartupAdmission(1,16384,reader=lambda _:free[0],max_initializing=2)
 assert a.acquire(0,0);free[0]=20000;assert not a.acquire(0,0) and a.pending[0]==1
 free[0]=40000;assert a.acquire(0,0) and not a.acquire(0,0);a.release(0);a.release(0)
 checks+=['two startup limit','unresolved peer8192MiB reservation','low free memory releases semaphore']
 def fail(_):raise TimeoutError('injected GPU query failure')
 b=m.StartupAdmission(1,16384,reader=fail,max_initializing=2)
 try:b.acquire(0,0)
 except TimeoutError:pass
 else:raise AssertionError('query error hidden')
 assert b.pending[0]==0;b.reader=lambda _:40000;assert b.acquire(0,0);b.release(0);checks+=['query error cannot leak reservation']
 old=m.StartupAdmission(1,16384,reader=lambda _:40000);assert old.acquire(0,0) and not old.acquire(0,0);old.release(0);checks+=['default single initializer compatibility']
 lock=threading.Lock();active=[0];maximum=[0];errors=[]
 def worker():
  try:
   for _ in range(60):
    if not a.acquire(0,.01):continue
    try:
     with lock:active[0]+=1;maximum[0]=max(maximum[0],active[0])
     time.sleep(.001)
     with lock:active[0]-=1
    finally:a.release(0)
  except Exception as e:errors.append(repr(e))
 ts=[threading.Thread(target=worker) for _ in range(8)]
 for t in ts:t.start()
 for t in ts:t.join()
 assert not errors and maximum[0]==2 and active[0]==a.pending[0]==0
 checks+=['8thread overlapping startup test']
 return {'passed':True,'CPU_only':True,'CUDA_calls':0,'checks':checks,'peak_concurrent_startups':maximum[0]}
if __name__=='__main__':
 result=main();(R/'STARTUP2_TESTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
