import json, sys, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D = '/tmp/claude-0/-root-lyf-safelab/961e3502-cdbc-46d7-9641-821bb9638ba3/scratchpad/table2/'
data = json.load(open(D + 'out/table2_srk.json'))
STYLE = {'TTS-Memory': ('#2a78d6', 'o', '-', 4), 'Mem-0': ('#eb6834', 's', '--', 3)}
ORDER = ['TTS-Memory', 'Mem-0']
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.edgecolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e', 'axes.linewidth': 0.6})
def fig_for(tasks, size, name):
    fig, axes = plt.subplots(1, len(tasks), figsize=size, sharey=True, squeeze=False)
    axes = axes[0]
    for ax, n in zip(axes, tasks):
        for m in ORDER:
            c = [x for x in data['curves'] if x['task'] == n and x['method'] == m]
            col, mk, ls, z = STYLE[m]
            ax.plot(range(1, n + 1), c[0]['srk'], color=col, ls=ls, lw=1.6, marker=mk, ms=4, mec='white', mew=0.5, zorder=z, label=m, clip_on=False)
        ax.set_title(f'{n}-subtask', fontsize=8.5); ax.set_xticks(range(1, n + 1)); ax.set_xlim(0.7, n + 0.3); ax.set_ylim(0, 100)
        ax.grid(axis='y', color='#e6e5e0', lw=0.5); ax.set_axisbelow(True)
        for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
        ax.set_xlabel('subtask k', fontsize=7.5)
    axes[0].set_ylabel('episodes completing ≥ k (%)', fontsize=7.5)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='upper center', ncol=2, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.05))
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    for ext in ['pdf', 'png']: fig.savefig(D + f'out/{name}.{ext}', dpi=300, bbox_inches='tight')
fig_for([3, 7], (3.5, 2.0), 'srk_tts_mem0_main_3_7')
fig_for([3, 5, 7, 10], (7.2, 2.1), 'srk_tts_mem0_all4')
fig_for([10], (3.3, 2.2), 'srk_tts_mem0_task10')
print('saved')
