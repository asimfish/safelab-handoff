import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D = '/tmp/claude-0/-root-lyf-safelab/961e3502-cdbc-46d7-9641-821bb9638ba3/scratchpad/table2/'
# Table 2 values (v1.2-relaxed, better horizon per method); see compute_table2_v12best.py
X = [3, 7, 10]
V = {'TTS-Memory': [67.8, 13.0, 1.0], 'Mem-0': [53.2, 7.3, 1.0]}
STYLE = {'TTS-Memory': ('#2a78d6', 'o', '-'), 'Mem-0': ('#eb6834', 's', '--')}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.edgecolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e', 'axes.linewidth': 0.6})
fig, ax = plt.subplots(figsize=(3.3, 2.2))
for m in ['TTS-Memory', 'Mem-0']:
    col, mk, ls = STYLE[m]
    ax.plot(X, V[m], color=col, ls=ls, lw=1.7, marker=mk, ms=4.5, mec='white', mew=0.5, label=m, clip_on=False)
    for x, v in zip(X, V[m]):
        if m == 'TTS-Memory': off, ha = (0, 6), 'center'
        elif x == 3: off, ha = (0, -11), 'center'
        elif x == 7: off, ha = (4, -12), 'left'
        else: off, ha = (7, -3), 'left'
        if m == 'TTS-Memory' and x == 10: off, ha = (-4, 7), 'right'
        ax.annotate(f'{v:.1f}', (x, v), textcoords='offset points', xytext=off, ha=ha, fontsize=6.8, color='#2b2b2b')
ax.set_xticks(X); ax.set_xticklabels(['3', '7', '10']); ax.set_xlim(2.4, 11.2); ax.set_ylim(0, 80)
ax.grid(axis='y', color='#e6e5e0', lw=0.5); ax.set_axisbelow(True)
for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
ax.set_xlabel('number of subtasks', fontsize=7.5); ax.set_ylabel('full-task success (%)', fontsize=7.5)
ax.legend(frameon=False, fontsize=7, loc='upper right')
fig.tight_layout()
for ext in ['pdf', 'png']: fig.savefig(D + f'out/success_vs_length_tts_mem0.{ext}', dpi=300, bbox_inches='tight')
print('saved')
