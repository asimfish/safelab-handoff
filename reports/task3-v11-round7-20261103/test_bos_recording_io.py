from pathlib import Path
import io,json,hashlib,numpy as np,h5py
from bos_recording_io import DeferredText,DeferredH5
root=Path('/projects/a02012413/buckets/zenith-a02012413/liyufeng/safelab_mem0_five_seed_pro8_20261029/round7/io_canary');root.mkdir(exist_ok=True)
t=DeferredText(root/'trace_canary.jsonl')
for i in range(100):t.write(json.dumps({'tick':i,'value':[i/120]*13})+'\n');t.flush()
t.close();assert len((root/'trace_canary.jsonl').read_text().splitlines())==100
f=DeferredH5(root/'particles_canary.h5',h5py.File);d=f.create_dataset('positions',shape=(0,1290,3),maxshape=(None,1290,3),chunks=(8,1290,3),compression='lzf',dtype='f8')
for i in range(100):d.resize(i+1,axis=0);d[i]=i/120;f.flush()
f.close()
with h5py.File(io.BytesIO((root/'particles_canary.h5').read_bytes()),'r') as v:assert v['positions'].shape==(100,1290,3);assert np.max(abs(v['positions'][99]-99/120))==0
print(json.dumps({'passed':True,'text_rows':100,'h5_frames':100,'metadata_only_pos':True,'large_outputs':str(root)}))
