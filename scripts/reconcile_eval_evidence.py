"""Reconcile known SafeLab source reports. Never starts or modifies evaluation jobs."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
OPS = Path('/home/liyufeng/ops')
AUDIT = OPS / 'safelab_handoff_portal_20261031/audit_20261031'
SWEEP = OPS / 'safelab_ours_threshold_sweep_20261028'
data = json.loads((SITE / 'data.json').read_text())
added = []
def put(e):
    data['evaluations'] = [x for x in data['evaluations'] if x['id'] != e['id']]
    data['evaluations'].append(e)
    added.append(e['id'])
def base(identifier, method, horizon, success, trials, unknown, source, kind, protocol, **extra):
    return dict(id=identifier,record='3-v13-'+method,dataset='3-v13',method={'mem0':'Mem-0','ours':'TTC（ours）','pi05':'pi0.5'}[method],checkpoint=30000,horizon=horizon,prediction=10 if method=='pi05' else 30,success=success,trials=trials,unknown=unknown,completed=trials,status='已完成',source=str(source),source_hash=hashlib.sha256(source.read_bytes()).hexdigest(),kind=kind,protocol=protocol,note='无法判定保留在固定分母中；不同实验口径不得合并。',**extra)

source = SWEEP / 'sr_eval_12gpu_20261029/FINAL_DELIVERY.json'
sr = json.loads(source.read_text())
assert sr['complete'] and sr['trials'] == 400 and sr['checkpoint'] == 30000
for c in sr['cells']:
    put(base(f"sr-v13-{c['method']}-{c['horizon']}",c['method'],c['horizon'],c['success'],c['target'],c['unknown'],source,'自主闭环 · SR复测',
        'task_event_sr_v1；单环境；A的XY各±1cm，50左/50右；取消额外安全/等待/净空门槛，不能当作原严格SSR；TTC阈值0.975',display_priority=100,result_label='SR任务成功率',metric='task_event_sr_v1',report_url=sr['public_url']))
source = SWEEP / 'FINAL_DELIVERY.json'
threshold = json.loads(source.read_text())
for c in threshold['final_rates']:
    suffix=str(c['threshold']).replace('.','')
    put(base(f"threshold-final-{suffix}-{c['horizon']}",'ours',c['horizon'],c['success'],c['total'],c['unknown'],source,'自主闭环 · 阈值留出测试',
        f"V13第三人称；单环境；A的XY各±1cm，50左/50右；阈值{c['threshold']}，累计2次；新留出100场景；原严格物理验收",
        threshold=c['threshold'],display_priority=80 if c['threshold']==0.975 else 70,result_label=f"严格验收·阈值{c['threshold']}",report_url=threshold['panel']))
source=OPS/'safelab_n4_causal_fix_20261028/FORMAL_SUCCESS_RATES.csv'
for c in csv.DictReader(source.read_text().splitlines()):
    h=int(c['execution_horizon'])
    put(base(f'n4-camera-fix-mem0-{h}','mem0',h,int(c['confirmed_success']),int(c['target']),int(c['observer_unknown']),source,'自主闭环 · 多环境相机候选',
        'V13第三人称30k；1cm，50左/50右；候选相机修正；192条四环境+8条两环境尾批；原严格验收',display_priority=-10,result_label='多环境相机候选'))
for e in data['evaluations']:
    if e['id'].startswith('single-v13-'):
        e.update(result_label='原严格验收', metric='legacy_physical_ssr')
# Incomplete trials must never become full-100 success rates.
source=OPS/'safelab_policy_parity_20261031/ACTUAL_SUCCESS_RATES.csv'
progress=list(csv.DictReader(source.read_text().splitlines()))
for e in data['evaluations']:
    if not e['id'].startswith('parity-'):continue
    method={'Mem-0':'mem0','TTC（ours）':'ours','pi0.5':'pi05'}[e['method']]
    parts=[r for r in progress if r['method']==method and int(r['horizon'])==e['horizon']]
    e.update(completed=sum(int(r['audited']) for r in parts),status='评测进行中（中途计数）',source=str(source),progress=[{'condition':r['condition'],'success':int(r['success']),'audited':int(r['audited']),'target':int(r['planned'])} for r in parts])
    e['note']='各条件目标100；尚未完成，不作为最终成功率。unknown_or_pending混合字段不当作已验收未知数。'

# Diagnostic outcomes are indexed alongside task records without replacing formal rates.
diag_source=OPS/'safelab_mem0_5b_single_gpu8_eval_20261029/training_input_eval_20261031/TRAINING_INPUT_RESULTS.json'
diag=json.loads(diag_source.read_text())
assert diag['complete'] and not diag['autonomous_closed_loop']
diags=[]
for h,c in diag['physical_success_rates'].items():
    diags.append(dict(id='five-training-input-'+h,record='5-fixed-mem0',dataset='5-fixed',camera='third_person',method='Mem-0',checkpoint=diag['checkpoint_step'],horizon=int(h),success=c['successes'],trials=c['trials'],unknown=0,completed=c['trials'],status='诊断已完成',kind='训练观测回放诊断（非自主闭环）',protocol='固定布局正反各一条；训练RGB+实测关节+GT子任务边界；模型预测动作进入原物理验收；不是100条自主成功率',source=str(diag_source),source_hash=hashlib.sha256(diag_source.read_bytes()).hexdigest(),note='独立专家动作对照2/2；本结果不替代正式600条基线。'))
for suffix,title in [('baseline','对照组'),('candidate','B归位新判定组')]:
    diags.append(dict(id='seven-b-return-'+suffix,record='7-mem0',dataset='7-weigh',camera='chest',method='Mem-0',checkpoint=None,horizon=None,success=2,trials=12,unknown=0,completed=12,status='诊断已完成（会话报告）',kind='归位判定诊断 · '+title,protocol='会话报告四卡24条试验，两组各12条；执行步数与具体checkpoint仍待报告文件核对；不并入原100条成功率',source='AnyGent tc4svfqatqlepu5ydrtcgel9e / 消息19387785',note='仅登记已核对的会话结果，不猜测权重步数与执行步数。'))
data['diagnostics']=diags

recent=json.loads((AUDIT/'recent.json').read_text())
inc_file=AUDIT/'incremental.json'
incs={i['conversation_id']:i for i in json.loads(inc_file.read_text())} if inc_file.exists() else {}
coverage=[]
for a in recent:
    p=json.loads((AUDIT/(a['conversation_id']+'-older.json')).read_text())
    pages=p['pages']
    assert p['count']==sum(page['count'] for page in pages)
    assert pages[0]['max_id']<a['range'][0]
    assert all(pages[i]['max_id']<pages[i-1]['min_id'] for i in range(1,len(pages)))
    inc=incs.get(a['conversation_id'],{})
    delta_pages=inc.get('pages',[])
    assert not delta_pages or delta_pages[0]['min_id']>a['range'][1]
    assert all(delta_pages[i]['min_id']>delta_pages[i-1]['max_id'] for i in range(1,len(delta_pages)))
    assert inc.get('count',0)==sum(page['count'] for page in delta_pages)
    coverage.append({'conversation_id':a['conversation_id'],'visible_messages_read':p['count']+a['count']+inc.get('count',0),'historical_messages_read':p['count']+a['count'],'incremental_messages_read':inc.get('count',0),'min_id':pages[-1]['min_id'],'max_id':inc.get('max_id',a['range'][1]),'reached_start':not pages[-1]['has_more'],'pagination_checked':True,'caught_up':inc.get('caught_up',False),'checked_at':inc.get('checked_at'),'latest_read_status':inc.get('status',a['status'])})
    agent=next((agent for agent in data['agents'] if agent['id']==a['conversation_id']),None)
    if agent:
        agent.update(read_count=coverage[-1]['visible_messages_read'],read_range=[coverage[-1]['min_id'],coverage[-1]['max_id']],checked_at=inc.get('checked_at',agent['checked_at']))
        messages=[m for m in inc.get('messages',[]) if m.get('text')]
        if messages:
            latest=max(messages,key=lambda m:m['id'])
            agent.update(last_message=latest['text'],last_message_id=latest['id'],summary=latest['text'].split('\n')[0][:400])
        agent['status']='会话运行中（作业状态需独立核对）' if inc.get('status',{}).get('is_running') else '会话已结束／后台作业需另核对'

assert len(coverage)==8 and all(c['reached_start'] for c in coverage)
data['evaluation_audit']={'checked_at':datetime.now(timezone.utc).isoformat(),'coverage':coverage,'visible_messages_read':sum(c['visible_messages_read'] for c in coverage),'added_or_reconciled_evaluations':added,'limitations':['仅覆盖读取时刻的8个会话可见历史；运行中的会话此后可能有新消息。','五任务TTC尚无已核对的权重/结果；用户澄清可能尚未评测，状态待确认。','初始基线的交付缺项不等于没有训练或没有评测。']}
data['coverage_notes']=[{'task':'5','method':'TTC（ours）','state':'五任务评测状态待确认','note':'用户澄清五任务TTC可能尚未评测。当前尚未核对到对应数据版本、相机、权重交付和4/8步成绩；请训练同学补交付后进入待测清单，不作为已评测结果。'}]
data['read_coverage']={'recent':sum(a['count'] for a in recent),'older':sum(c['historical_messages_read'] for c in coverage)-sum(a['count'] for a in recent),'incremental':sum(c['incremental_messages_read'] for c in coverage)}
# Keep the imported snapshot timestamp; the separate audit timestamp identifies this reconciliation.
(SITE/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'new_reports':len(added),'evaluations':len(data['evaluations']),'messages_read':sum(c['visible_messages_read'] for c in coverage),'conversations':len(coverage)},ensure_ascii=False))
