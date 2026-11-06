#!/usr/bin/env python3
"""Import SHA-pinned task5 producer evidence; never infer missing measurements."""
import argparse, datetime, gzip, hashlib, json, pathlib, tarfile, urllib.parse
SHA = {'TASK5_MEDIA_MANIFEST_v2_1.json':'d08cfcd4278faa91f46f4207ccb1785692513de038aa963c62033e39461c1793','TASK5_SCENE_INDEX_TO_ID_v2.json':'eb105bb6737c34bbad7d9c0c4f42ec50b5d9d0dd016d78b020350a5f486a7635','TASK5_MEDIA_METADATA_v2_1.tar.gz':'189ccd2db48c4de8dc301376ae0257c4162692091cc0abfa891a48cd88305322'}
BASE='https://asimfish.github.io/safelab-handoff/'
def digest(b): return hashlib.sha256(b).hexdigest()
def packed(x): return (json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def run(root, inputs):
    root=root.resolve(); blobs={}
    manifests=sorted((root/'media/manifests/5').glob('task5-t939-*-20261106.json'))
    if any(c.get('metadata_v21_source_sha256') for f in manifests for c in json.loads(f.read_bytes())['cases']):
        raise ValueError('v2.1 already imported; refusing to overwrite migration originals')
    for name,sha in SHA.items():
        b=(inputs/name).read_bytes(); assert len(b)<15000000 and digest(b)==sha,name; blobs[name]=b
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    source=json.loads(blobs['TASK5_MEDIA_MANIFEST_v2_1.json']); cases={c['case_id']:c for c in source['cases']}; members={}
    with tarfile.open(inputs/'TASK5_MEDIA_METADATA_v2_1.tar.gz') as tar:
        assert len(tar.getmembers())<200 and sum(m.size for m in tar.getmembers())<10000000
        for m in tar.getmembers():
            p=pathlib.PurePosixPath(m.name)
            assert m.isfile() and not p.is_absolute() and '..' not in p.parts and m.size<2000000,m.name
            assert m.name not in members
            members[m.name]=tar.extractfile(m).read()
    assert members['TASK5_MEDIA_MANIFEST_v2_1.json']==blobs['TASK5_MEDIA_MANIFEST_v2_1.json']
    assert members['TASK5_SCENE_INDEX_TO_ID_v2.json']==blobs['TASK5_SCENE_INDEX_TO_ID_v2.json']
    report={'source_sha256':SHA,'scope':'diagnostic strict declared-scene/seed/recorded-optics pairing; not bitwise initial-state equality or formal-score promotion','cases':[]}
    for manifest in manifests:
        doc=json.loads(manifest.read_bytes());doc.update(updated_at=now,metadata_source_updated_at=source['updated_at'])
        for c in doc['cases']:
            s=cases[c['case_id']]
            c['metadata_v21_source_sha256']=SHA['TASK5_MEDIA_MANIFEST_v2_1.json']
            c['formal_score_eligible']=False
            if s['status']!='published_verified':
                c['metadata_missing_reasons']=s['metadata_missing_reasons'];continue
            assert c['stage']=='diagnostic' and s['protocol_version']=='SafeLab-Eval-v1.1'
            refs={}; raw={}
            for kind,key,folder in [('switch','raw_model_switches','model_switch_logs'),('scene','raw_scene_metadata','scene_evidence')]:
                b=members[f'{folder}/{c["case_id"]}.json'];a=s[key]
                assert digest(b)==a['sha256'] and len(b)==a['bytes']
                obj=json.loads(b);assert obj['case_id']==c['case_id'] and obj['source_archive_sha256']==s['source_archive_sha256']
                out=root/f'media/evidence/5/t939-v21/{folder}/{c["case_id"]}.json.gz';out.parent.mkdir(parents=True,exist_ok=True);wire=gzip.compress(b,mtime=0);out.write_bytes(wire)
                refs[kind]={'url':BASE+str(out.relative_to(root)),'encoding':'gzip','sha256':digest(wire),'bytes':len(wire),'decoded_sha256':digest(b),'decoded_bytes':len(b)};raw[kind]=obj
            assert raw['scene']['declared_scene']==s['scientific_scene_fields']
            assert raw['scene']['render_config_hash']==s['render_config_hash']
            for key in ['scene_seed','policy_seed','scene_list_hash','render_config_hash','protocol_version','declared_scene_hash','scene_profile_sha256','scientific_scene_fields','subtask_mapping_semantics','subtask_mapping_source','subtask_physical_targets','oracle_phase_targets','physical_equivalence_status','actual_initial_readback_hash']:
                c[key]=s.get(key)
            c.update(seed=s['policy_seed'],condition_version=s['condition_version'],task5_pairing_version='t939-v2.1',metadata_evidence=refs,model_switching_applicable=raw['switch']['model_switching_applicable'])
            for key in list(c):
                if key.startswith('preview_'):del c[key]
            logpath=root/urllib.parse.urlparse(c['frame_log']['url']).path.removeprefix('/safelab-handoff/')
            old=logpath.read_bytes();assert digest(old)==c['frame_log']['sha256']
            archive=inputs/'task5-v21-log-originals'/logpath.relative_to(root);archive.parent.mkdir(parents=True,exist_ok=True)
            if archive.exists():assert archive.read_bytes()==old
            else:archive.write_bytes(old)
            log=json.loads(gzip.decompress(old));rows=log['rows']; byframe={r['frame']:r for r in rows}
            for r in rows:
                r['completion_probability']=r.get('completion_score');r['probability_threshold']=r.get('threshold');r['completion_score']=None;r['threshold']=None
            for a in raw['switch']['records']:
                tr=a.get('raw_completion_trace') or {};dec=tr.get('decision') or {};status=dec.get('status') or {};before=tr.get('before') or {};frame=a['frame']
                r=byframe.get(frame)
                if r is None:
                    prior=max((v for v in rows if v['frame']<frame),key=lambda v:v['frame'],default=None)
                    r={'frame':frame,'t_sim':a['t_sim'],'physical_phase':prior.get('physical_phase') if prior else None,'physical_events':[]};rows.append(r);byframe[frame]=r
                assert abs(r['t_sim']-a['t_sim'])<1e-7
                r.update(active_subtask_index=a['raw_stage'],subtask_index=before.get('stage',a['raw_stage']),completion_score=status.get('completion_score'),threshold=dec.get('completion_score_threshold'),completion_probability=dec.get('completion_probability'),probability_threshold=dec.get('probability_threshold'),positive_count=dec.get('positive_count'),switched=tr.get('switched',False),raw_switch_record=True)
                if tr.get('switched'):r.update(model_switch_t_sim=a['t_sim'],switch_from_index=before.get('stage'),score_attribution='previous_subtask_at_switch')
            rows.sort(key=lambda r:(r['t_sim'],r['frame']))
            # Raw export retains every stage change. Forward-fill only its observed
            # stage, never the older summary's physical/planner proxy index.
            active=None
            for row in rows:
                if row.get('raw_switch_record'):active=row.get('active_subtask_index')
                row['producer_summary_subtask_index']=row.get('subtask_index')
                row['active_subtask_index']=active
                row['subtask_index']=row.get('switch_from_index') if row.get('switched') else active
            log['sampling']['retained_rows']=len(rows);log['metadata_v21_evidence']=refs;log['model_switching_applicable']=raw['switch']['model_switching_applicable'];log['score_semantics']='completion_score from raw status only; completion_probability is separate; sparse raw score samples are not inferred between events'
            decoded=packed(log);wire=gzip.compress(decoded,mtime=0);assert len(decoded)<=2000000;logpath.write_bytes(wire)
            c['frame_log'].update(sha256=digest(wire),bytes=len(wire),decoded_sha256=digest(decoded),decoded_bytes=len(decoded))
            report['cases'].append({'case_id':c['case_id'],'scene_index':c['scene_index'],'method':c['method'],'horizon':c['horizon'],'switch_records':len(raw['switch']['records']),'switches':sum(bool((r.get('raw_completion_trace') or {}).get('switched')) for r in raw['switch']['records']),'evidence':refs})
        manifest.write_bytes(packed(doc))
    idx=root/'media/index.json';j=json.loads(idx.read_bytes());j['updated_at']=now
    for ref in j['manifests']:
        path=root/urllib.parse.urlparse(ref['url']).path.removeprefix('/safelab-handoff/');ref['sha256']=digest(path.read_bytes())
        if '/5/task5-t939-' in ref['url']:ref['updated_at']=now
    idx.write_bytes(packed(j))
    out=root/'all_task_videos/task5-metadata-v21-verification.json';out.write_bytes(packed(report));print(json.dumps({'verified_cases':len(report['cases']),'switches':sum(c['switches'] for c in report['cases'])}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=pathlib.Path,required=True);a=p.parse_args();run(pathlib.Path(__file__).resolve().parents[1],a.inputs.resolve())
