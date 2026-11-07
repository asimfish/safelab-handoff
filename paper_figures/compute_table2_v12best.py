"""Table 2 variant: most lenient oracle archived for every cell (SafeLab-Eval-v1.2-relaxed), each method at its better
execution horizon (h4 or h8) per task. Cells without an archived v1.2 row use the v1.1 value (a lower bound, marked ‡)."""
import json, os
D = os.path.dirname(os.path.abspath(__file__)) + '/'
E = {e['id']: e for e in json.load(open(D + 'data.json'))['evaluations']}
def r(i): return E[i]['success'], E[i]['trials']
def pool(ids):
    s = t = 0
    for i in ids: a, b = r(i); s += a; t += b
    return s, t
C = {  # (method, task) -> {h: (success, trials, flag)}
 ('TTS-Memory', 3): {4: r('t1035-v12-relaxed-a7eca15f87219dcc') + ('',), 8: r('t1035-v12-relaxed-a519cc9bf4efbf10') + ('',)},
 ('Mem-0', 3): {4: r('t1035-v12-relaxed-978e239f2ee2ca72') + ('',), 8: r('t1035-v12-relaxed-13bcde0ec5f93079') + ('',)},
 ('MemoryVLA', 3): {4: r('t1035-memoryvla73-final-h4-relaxed-20261106') + ('',), 8: r('t1035-memoryvla73-final-h8-relaxed-20261106') + ('',)},
 ('π0.5', 3): {4: (0, 100, '‡'), 8: (4, 100, '‡')},  # 40k v1.1 (agent table TABLE2_V11.json); v1.2 not archived
 ('TTS-Memory', 5): {4: r('task5-t939-20261106-ours-h4-v12') + ('',), 8: r('task5-t939-20261106-ours-h8-v12') + ('',)},
 ('Mem-0', 5): {4: r('task5-t939-20261106-mem0-h4-v12') + ('',), 8: r('task5-t939-20261106-mem0-h8-v12') + ('',)},
 ('MemoryVLA', 5): {4: r('task5-t939-20261106-memoryvla-h4-v12') + ('',), 8: r('task5-t939-20261106-memoryvla-h8-v12') + ('',)},
 ('π0.5', 5): {8: r('task5-relaxed-20261105-874b89ec0996e066') + ('',)},
 ('TTS-Memory', 7): {4: r('task7-new-raw-ours_aligned_30k-h4-seed0-20261106-v1_2') + ('',),
                     8: pool(['task7-rescore-v12-relaxed-original-ours_aligned_30k-h8-A739-20261105', 'task7-new-raw-ours_aligned_30k-h8-seed1-20261106-v1_2', 'task7-new-raw-ours_aligned_30k-h8-seed2-20261106-v1_2']) + ('',)},
 ('Mem-0', 7): {4: (5, 100, ''),  # A3 corrected rescore, v1.2 (agent-reported)
                8: pool(['task7-rescore-v12-relaxed-original-mem0_30k-h8-A739-20261105', 'task7-new-raw-mem0_30k-h8-seed1-20261106-v1_2', 'task7-new-raw-mem0_30k-h8-seed2-20261106-v1_2']) + ('',)},
 ('π0.5', 7): {4: r('task7-pi05-source-v11-h4-archive-20261106') + ('‡',), 8: r('task7-pi05-source-v11-h8-archive-20261106') + ('‡',)},
 ('TTS-Memory', 10): {4: r('task10-v12-relaxed-20261105-ours_aligned-30k-h4-original-legacy') + ('',), 8: r('task10-v12-relaxed-20261105-ours_aligned-30k-h8-original-legacy') + ('',)},
 ('Mem-0', 10): {4: r('task10-recovery136-20261106-mem0_original-30k-h4-original-placement-diagnostic') + ('‡',), 8: r('task10-recovery136-20261106-mem0_original-30k-h8-original-placement-diagnostic') + ('‡',)},
 ('MemoryVLA', 10): {4: (0, 100, ''), 8: (0, 100, '')},  # stage-10 report v12 block
 ('π0.5', 10): {4: (0, 100, ''), 8: (0, 100, '')},
}
rows = []
for m in ['π0.5', 'Mem-0', 'MemoryVLA', 'TTS-Memory']:
    line = [m]; vals = []
    for t in [3, 5, 7, 10]:
        c = C.get((m, t))
        if not c: line.append('—'); continue
        h, (s, n, f) = max(c.items(), key=lambda kv: kv[1][0] / kv[1][1])
        v = 100 * s / n; vals.append(v)
        line.append('%.1f%s (h%d, %d/%d)' % (v, f, h, s, n))
    line.append('%.1f' % (sum(vals) / 4) if len(vals) == 4 else '—')
    rows.append(line)
for l in rows: print(' | '.join(l))
