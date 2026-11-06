"""Publish only prepared small recovery stats and exact compressed index fragments."""
from pathlib import Path
import json,hashlib,gzip,argparse,shutil,datetime,html
N=Path('/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027');R=N/'eval_v11_admission_20261104/eval_v12_relaxed_cpu_20261105';W=N/'v1_website_inventory_20261103/review-repo';P=W/'reports/task7-v12-relaxed-20261105';H=P/'history_math';O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_bytes())
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
def ref(p):return {'file':p.relative_to(W).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
def publish(plan):
 D=H/'recovered_after_v1';assert not D.exists();D.mkdir();cohorts=[];all_new=[]
 for item in plan['cohorts']:
  directory=Path(item['directory']);source=load(directory/'summary.json');assert source['actual_existing_case_n']==item['n'];dest=D/item['name'];dest.mkdir();rebuilt=[]
  for c in source['source_index']['chunks']:
   f=directory/c['file'];assert f.stat().st_size==c['bytes']and sha(f)==c['sha256'];decoded=gzip.decompress(f.read_bytes());assert len(decoded)==c['decoded_bytes']and hashlib.sha256(decoded).hexdigest()==c['decoded_sha256'];rebuilt.append(decoded);shutil.copyfile(f,dest/f.name)
  assert hashlib.sha256(b''.join(rebuilt)).hexdigest()==source['source_index']['sha256'];shutil.copyfile(directory/'summary.json',dest/'summary.json');all_new+=load(directory/'PRIVATE_SELECTED_ROWS_NOT_FOR_PUBLICATION.json')['rows'];cohorts.append({'name':item['name'],'label':item['label'],'n':item['n'],'summary':ref(dest/'summary.json'),'original_index_sha256':source['source_index']['sha256']})
 # Exact source identity and raw reference overlap, including all original main cases.
 previous=[]
 for part in load(H/'summary.json')['parts']:previous+=load(W/part['file'])['rows']
 main=load(R/'report_v1/ACTUAL_MAIN200_ALL7_UNKNOWN_AWARE/RECORDS.json')['records']
 prior_identity={(x['variant'],x['horizon'],x['case_id'])for x in previous}|{(x['configuration_id'],8,x['case_id'])for x in main};new_identity={(x['variant'],x['horizon'],x['case_id'])for x in all_new};assert len(new_identity)==len(all_new)and not(prior_identity&new_identity)
 prior_raw={x['raw']['sha256']for x in previous if x['raw']}|{r['sha256']for x in main for r in x['raw_refs']};new_raw={x['raw']['sha256']for x in all_new if x['raw']};assert not(prior_raw&new_raw),'Requires explicit root adjudication before publication of raw-SHA overlap'
 sources={}
 for item in plan['exact_small_sources']:
  f=Path(item['file']);assert sha(f)==item['sha256']and f.stat().st_size<200000;dest=D/item['public_name'];shutil.copyfile(f,dest);sources[item['public_name']]=ref(dest)
 for name in ['build_recovery_stats.py','publish_recovery.py']:
  shutil.copyfile(O/name,D/name);sources[name]=ref(D/name)
 summary={'schema':'task7_recovered_original_history_publication.v1','updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stage':'diagnostic','metric_role':'historical_contact_math_appendix','formal_score_eligible':False,'formal_placement_success':None,'main_data_evaluation_rows_changed':False,'data_json_sha256':sha(W/'data.json'),'cohorts':cohorts,'newly_processed_existing_historical_cases':len(all_new),'full_raw_SHA_verified_by_worker_n':sum(x['raw_SHA_verified']for x in all_new),'raw_unavailable_n':sum(not x['raw_SHA_verified']for x in all_new),'canonical_v11_U':len(all_new),'canonical_relaxed_U':len(all_new),'new_raw_NN_GPU_API_reads_calls':0,'original_cached_small_receipts_SHA_verified_n':len(all_new),'prior_main_and_historical_source_identities_n':len(prior_identity),'source_identity_overlap_n':0,'full_raw_SHA_overlap_with_prior_n':0,'earlier_history_cases_n':2385,'main_cases_n':200,'all_known_unique_case_inventory_n':len(all_new)+2385+200,'global_pooled_SR':None,'sources':sources,'boundaries':['Different methods, checkpoints, horizons and source conditions are separate groups; no global pooled SR.','All recovered historical placement verdicts remain canonical U due unqualified complete all-Robot contact coverage. Math S/F/U is an appendix only.','Strict original scores are source audit/RESULT/finalphase bindings, not a newly completed strict replay.','Old source variant/condition retained; chain/attachment/resize/completionfix not inferred from names.','Earlier V1 missing-index notes are historical. Exact recovery+CPU evidence below supersedes their availability status without rewriting V1 bytes.','20000-step ours6 h4/h8 cases are already in2265; h30 baseline2 occurs only in the new h30 cohort. Remaining1495 weak-aligned campaign target slots were not completed cases and are not manufactured U.']};dump(D/'summary.json',summary)
 esc=lambda s:html.escape(str(s));fmt=lambda v:'null'if v is None else f'{v:.6f}'if isinstance(v,float)else str(v);sf=lambda m:'/'.join(str(m[k])for k in ['S','F','U']);body=['<h1>旧original与h30恢复：独立接触数学附录</h1>','<p>主表及原366评测记录不变。这里补充已存在历史病例的数学重算，canonical placement仍全部U，未补全机器人接触覆盖。不同批次不能汇总SR。此前V1“未取得完整索引”只是当时状态，已由后续精确恢复/CPU证据更新，原证据字节不覆盖。</p>','<p>每个源索引按原字节切分、gzip压缩；逐片wire/解压SHA及拼接后的完整原索引SHA均核验。病例原小CPU收据逐SHA核，原worker完整raw读取另记；本发布器不读raw、不调新oracle/NN/GPU。</p>']
 for item in cohorts:
  s=load(W/item['summary']['file']);body+=['<h2>'+esc(item['label'])+'</h2>',f'<p>实际已有病例{s["actual_existing_case_n"]}，原worker全raw SHA {s["full_raw_SHA_verified_by_original_worker_n"]}，原raw不可用{s["raw_unavailable_n"]}；规范两放置口径均U {s["actual_existing_case_n"]}，不是正式新成绩。<a href="{item["name"]}/summary.json">所有阶段、Wilsons、均值、原始压缩索引SHA</a>。</p>','<table><thead><tr><th>原variant / ckpt</th><th>h / 原condition</th><th>实际N/raw</th><th>数学v1.1→relaxed S/F/U</th><th>SR@4已确认S/N（及U）</th><th>有效phase均值/n</th></tr></thead><tbody>']
  for g in s['groups']:
   a=g['math']['v1.1'];b=g['math']['v1.2-relaxed'];ka=a['per_stage']['4'];kb=b['per_stage']['4'];body.append('<tr><td>'+esc(g['variant'])+'/'+str(g['checkpoint'])+'</td><td>'+str(g['horizon'])+'/'+esc(g['condition'])+'</td><td>'+str(g['n_actual_historical_cases'])+'/'+str(g['raw_full_SHA_CPU_verified_n'])+'</td><td>'+sf(a)+' → '+sf(b)+'</td><td>'+str(ka['S'])+'/'+str(ka['N'])+' (U'+str(ka['U'])+') → '+str(kb['S'])+'/'+str(kb['N'])+' (U'+str(kb['U'])+')</td><td>'+fmt(a['mean_phase_valid_closed_only'])+'/'+str(a['mean_phase_n'])+' → '+fmt(b['mean_phase_valid_closed_only'])+'/'+str(b['mean_phase_n'])+'</td></tr>')
  body+=['</tbody></table>']
 body+=['<h2>计数与旧证据边界</h2>',f'<p>本次新增处理{len(all_new)}个已有历史病例；与先前2385辅助及200主病例按源identity和rawSHA检查无重合，已知总库存{summary["all_known_unique_case_inventory_n"]}（不是可汇总的共同SR分母）。原六条ours20k h4/h8 baseline不重复；新h30单列。#18旧独立assisted campaign仅实际5条，其余1495目标未完成，不当unknown试验。pi05只有交付record，未取得本agent可验证eval/raw索引，不造trials。</p>','<p>未知保留实际每组N；S/N/Wilson只标已确认成功指示量，trueSR有U时为null并列界限。均值仅已知whole有效phase，已观察但删失的阶段下界及逐阶段S/F/U另列。旧strict没有完整新执行。</p>','<ul>']
 for name,r in sources.items():body.append('<li><a href="'+esc(name)+'">'+esc(name)+'</a> · <code>'+r['sha256']+'</code></li>')
 body+=['<li><a href="summary.json">发布索引/病例重合检查/源SHA</a></li></ul><p><a href="../index.html">返回历史附录</a> · <a href="../../index.html">返回主200诊断</a>。仅PR待审，未自行合并。</p>'];(D/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>旧原始N1与h30恢复数学附录</title><link rel="stylesheet" href="../../../../style.css"><main style="max-width:1300px;margin:2rem auto;padding:1rem">'+''.join(body)+'</main></html>\n')
 for page in [H/'index.html',P/'index.html']:
  text=page.read_text();head='<section id="recovered-original-history-current"><h2>后续恢复已完成：旧original与h30数学附录</h2><p>原先缺完整索引的旧original30k1000、Mem0_20k200现已恢复；另h30及#18实际5例按独立源批次追加。旧覆盖V1原字节保留、以恢复证据更新当前可用性，canonical仍因接触覆盖缺证全U。主表和data不变，不把目标未完成数当U。<a href="'+('recovered_after_v1/index.html'if page.parent==H else'history_math/recovered_after_v1/index.html')+'">最终恢复数学表/压缩原索引/逐组未知与来源</a>。</p></section>';text=text.replace('<h1>',head+'<h1>',1)
  text=text.replace('尚未取得完整raw/Scene索引的独立coverage见','首版未取得完整raw/Scene索引、现已恢复数学重算的独立coverage见')
  text=text.replace('本有界核查尚未取得完整raw路径+SHA+Scene/closure/可读性索引，故本轮没有重算这些原100格','首版有界核查当时尚未取得完整raw路径+SHA+Scene/closure/可读性索引，故该时点尚未重算这些原100格（后续恢复已见上方新附录）')
  text=text.replace('未取得完整raw/Scene索引；新判定未重算','V1未取得完整索引；现已恢复数学重算，见上方新附录')
  text=text.replace('h30共1030本轮未重算。','首版未含h30共1030；后续恢复已在上方新附录单列。')
  text=text.replace('h30历史1030仅覆盖注记，本轮未重算，不从旧摘要补新数学分数。','首版h30历史1030仅覆盖注记，当时未重算；后续完整恢复已由上方新附录单列，不从旧摘要补分。')
  page.write_text(text)
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);a=p.parse_args();s=publish(load(a.plan));print(json.dumps({'new_historical_n':s['newly_processed_existing_historical_cases'],'known_inventory_n':s['all_known_unique_case_inventory_n'],'data_sha256':s['data_json_sha256']}))
