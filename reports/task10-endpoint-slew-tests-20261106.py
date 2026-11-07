from pathlib import Path
import argparse, hashlib, importlib.util, json
import numpy as np

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--module',type=Path,required=True)
    ap.add_argument('--parameters',type=Path,required=True)
    ap.add_argument('--experts',type=Path,required=True)
    a=ap.parse_args();parameters=json.loads(a.parameters.read_text())
    spec=importlib.util.spec_from_file_location('endpoint_slew_under_test',a.module)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    frames=0
    for entry in parameters['experts']:
        p=a.experts/entry['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
        seq=np.load(p)['endpoints'].astype(np.float32)
        f=m.EndpointSlew(parameters['initial_commands'][entry['file']],parameters)
        out=np.asarray([f.step(row)for row in seq])
        assert np.array_equal(out,seq) and f.clamped_frames==0,entry['file'];frames+=len(seq)
    f=m.EndpointSlew(np.zeros(13),parameters);positions=[np.zeros(13)]
    for target in np.random.default_rng(20261106).uniform(-2,2,size=(1000,13)):positions.append(f.step(target))
    v=np.diff(np.asarray(positions,dtype=float),axis=0)*parameters['Hz']
    acc=np.diff(np.vstack([np.zeros(13),v]),axis=0)*parameters['Hz']
    assert np.max(np.abs(v)-np.asarray(parameters['velocity_limit_rad_s']))<2e-5
    assert np.max(np.abs(acc)-np.asarray(parameters['acceleration_limit_rad_s2']))<1e-3
    f=m.EndpointSlew(np.zeros(13),parameters)
    out=np.asarray([f.step(np.ones(13)*.5)for _ in range(3000)])
    assert np.max(np.abs(out[-100:]-.5))<1e-6,'stationary target must settle without self oscillation'
    f1=m.EndpointSlew(np.zeros(13),parameters);f2=m.EndpointSlew(np.zeros(13),parameters)
    first=f1.step(np.ones(13));assert np.array_equal(first,f2.step(np.ones(13)))
    f1.step(-np.ones(13));assert np.array_equal(f2.p,first),'lane state must be private'
    for target in [np.zeros(12),np.full(13,np.nan)]:
        try:f2.step(target)
        except ValueError:pass
        else:raise AssertionError('invalid endpoint accepted')
    print(json.dumps({'passed':True,'experts':len(parameters['experts']),'expert_frames_bitwise_equal':frames,'properties':['velocity bounds','acceleration bounds','stationary target convergence','private state','deterministic reset','invalid action rejection'],'parameters_sha256':hashlib.sha256(a.parameters.read_bytes()).hexdigest(),'module_sha256':hashlib.sha256(a.module.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
