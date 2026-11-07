"""Table 2 + SR@k from data.json (v1.1, unassisted). Cells not in data.json come from EXTRA (agent-reported)."""
import json, gzip, math, csv, sys
import os
D = os.path.dirname(os.path.abspath(__file__)) + '/'
def _load_data():
    if os.path.exists(D + 'data.json'):
        return json.load(open(D + 'data.json'))
    return json.load(gzip.open(D + 'data.json.gz', 'rt', encoding='utf-8'))
d = _load_data()
E = {e['id']: e for e in d['evaluations']}
N = {3: 3, 5: 5, 7: 7, 10: 10}
# (task, method) -> {horizon: [row ids]}
SEL = {
 (3, 'TTS-Memory'): {4: ['t1035-final-ttc-V13-trainresize-B-placement-c30000-h4'], 8: ['t1035-final-ttc-V13-trainresize-B-placement-c30000-h8']},
 (3, 'Mem-0'): {4: ['t1035-final-mem0-V13-trainresize-B-placement-c30000-h4'], 8: ['t1035-final-mem0-V13-trainresize-B-placement-c30000-h8']},
 (3, 'MemoryVLA'): {4: ['t1035-memoryvla73-final-h4-v11-20261106'], 8: ['t1035-memoryvla73-final-h8-v11-20261106']},
 (5, 'TTS-Memory'): {4: ['task5-t939-20261106-ours-h4-v11'], 8: ['task5-t939-20261106-ours-h8-v11']},
 (5, 'Mem-0'): {4: ['task5-t939-20261106-mem0-h4-v11'], 8: ['task5-t939-20261106-mem0-h8-v11']},
 (5, 'MemoryVLA'): {4: ['task5-t939-20261106-memoryvla-h4-v11'], 8: ['task5-t939-20261106-memoryvla-h8-v11']},
 (7, 'TTS-Memory'): {4: ['task7-new-raw-ours_aligned_30k-h4-seed0-20261106-v1_1'],
                     8: ['task7-eval-v11-A-original-ttc_aligned_trainresize_30k-h8', 'task7-new-raw-ours_aligned_30k-h8-seed1-20261106-v1_1', 'task7-new-raw-ours_aligned_30k-h8-seed2-20261106-v1_1']},
 (7, 'Mem-0'): {8: ['task7-eval-v11-A-original-mem0_30k-h8', 'task7-new-raw-mem0_30k-h8-seed1-20261106-v1_1', 'task7-new-raw-mem0_30k-h8-seed2-20261106-v1_1']},
 (7, 'π0.5'): {4: ['task7-pi05-source-v11-h4-archive-20261106'], 8: ['task7-pi05-source-v11-h8-archive-20261106']},
 (10, 'TTS-Memory'): {4: ['task10-eval-v1-20261103-ours_aligned-off-h4'], 8: ['task10-eval-v1-20261103-ours_aligned-off-h8']},
 (10, 'Mem-0'): {4: ['task10-recovery136-20261106-mem0_original-30k-h4-original-placement-diagnostic'], 8: ['task10-recovery136-20261106-mem0_original-30k-h8-original-placement-diagnostic']},
}
# agent-reported cells (filled when replies arrive): (task, method) -> {h: dict(success, trials, unknown, phase_hist)}
EXTRA = json.load(open(D + 'agent_reported_cells.json')) if len(sys.argv) > 1 else {}
def rowdata(rid):
    e = E[[k for k in E if k.startswith(rid)][0]] if rid not in E else E[rid]
    return dict(success=e['success'], trials=e['trials'], unknown=e.get('unknown') or 0, phase_hist={int(k): v for k, v in (e.get('phase_hist') or {}).items()}, id=e['id'])
cells = {}
for key, hs in SEL.items():
    cells[key] = {}
    for h, ids in hs.items():
        agg = dict(success=0, trials=0, unknown=0, phase_hist={}, ids=[])
        for rid in ids:
            r = rowdata(rid)
            agg['success'] += r['success']; agg['trials'] += r['trials']; agg['unknown'] += r['unknown']; agg['ids'].append(r['id'])
            for k, v in r['phase_hist'].items(): agg['phase_hist'][k] = agg['phase_hist'].get(k, 0) + v
        cells[key][h] = agg
for k, hs in EXTRA.items():
    t, m = k.split('|'); t = int(t)
    cells.setdefault((t, m), {})
    for h, v in hs.items():
        v['phase_hist'] = None if v['phase_hist'] is None else {int(a): b for a, b in v['phase_hist'].items()}; v['ids'] = [v.get('source', 'agent-reported')]
        cells[(t, m)][int(h)] = v
def srk(c, n):
    T = c['trials']; ph = c['phase_hist']
    return [100.0 * sum(v for p, v in ph.items() if p >= k) / T for k in range(1, n + 1)]
METHODS = ['π0.5', 'Mem-0', 'MemoryVLA', 'TTS-Memory']
rows = []; curves = []
for m in METHODS:
    line = [m]; vals = []
    for t in [3, 5, 7, 10]:
        c = cells.get((t, m))
        if not c:
            line.append('—'); continue
        rates = [100.0 * c[h]['success'] / c[h]['trials'] for h in sorted(c)]
        avg = sum(rates) / len(rates); vals.append(avg)
        line.append('%.1f' % avg + ('' if len(c) == 2 else '*'))
        hs = [h for h in sorted(c) if c[h]['phase_hist'] is not None]
        if not hs: continue
        curve = [sum(x) / len(hs) for x in zip(*[srk(c[h], N[t]) for h in hs])]
        curves.append((t, m, curve, {h: (c[h]['success'], c[h]['trials'], c[h]['unknown']) for h in hs}))
    line.append('%.1f' % (sum(vals) / 4) if len(vals) == 4 else '—')
    rows.append(line)
print('Method | 3 | 5 | 7 | 10 | Avg')
for r in rows: print(' | '.join(r))
print()
for t, m, cv, det in curves:
    print(t, m, det, ['%.1f' % x for x in cv])
json.dump({'rows': rows, 'curves': [dict(task=t, method=m, srk=cv, detail={str(h): v for h, v in det.items()}) for t, m, cv, det in curves]}, open(D + 'out/table2_srk.json', 'w'), ensure_ascii=False, indent=1)
with open(D + 'out/srk.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['task', 'method', 'k', 'SR_at_k_percent'])
    for t, m, cv, det in curves:
        for k, v in enumerate(cv, 1): w.writerow([t, m, k, round(v, 2)])
