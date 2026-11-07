import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
D = os.path.dirname(os.path.abspath(__file__)) + '/'
data = json.load(open(D + 'out/table2_srk.json'))
STYLE = {  # fixed categorical order; markers + dashes as secondary encoding (print / CVD)
    'TTS-Memory': dict(color='#2a78d6', marker='o', ls='-', z=4),
    'Mem-0': dict(color='#eb6834', marker='s', ls='-', z=3),
    'MemoryVLA': dict(color='#1baf7a', marker='^', ls='--', z=2),
    'π0.5': dict(color='#eda100', marker='D', ls=':', z=1),
}
ORDER = ['TTS-Memory', 'Mem-0', 'MemoryVLA', 'π0.5']
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.edgecolor': '#52514e', 'axes.labelcolor': '#0b0b0b',
                     'xtick.color': '#52514e', 'ytick.color': '#52514e', 'axes.linewidth': 0.6})
fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.15), sharey=True)
for ax, n in zip(axes, [3, 5, 7, 10]):
    for m in ORDER:
        c = [x for x in data['curves'] if x['task'] == n and x['method'] == m]
        if not c: continue
        s = STYLE[m]; y = c[0]['srk']; x = list(range(1, n + 1))
        ax.plot(x, y, color=s['color'], ls=s['ls'], lw=1.5, marker=s['marker'], ms=4.2, mec='white', mew=0.6, zorder=s['z'], label=m, clip_on=False)
    ax.set_title(f'{n}-subtask', fontsize=8.5, color='#0b0b0b', pad=4)
    ax.set_xticks(range(1, n + 1)); ax.set_xlim(0.7, n + 0.3); ax.set_ylim(0, 100)
    ax.grid(axis='y', color='#e6e5e0', lw=0.6); ax.set_axisbelow(True)
    for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
    ax.set_xlabel('subtask k', fontsize=7.5)
axes[0].set_ylabel('episodes completing ≥ k\nsubtasks (%)', fontsize=7.5)
h, l = axes[0].get_legend_handles_labels()
seen = {}
for ax in axes:
    for hh, ll in zip(*ax.get_legend_handles_labels()): seen.setdefault(ll, hh)
fig.legend([seen[m] for m in ORDER if m in seen], [m for m in ORDER if m in seen], loc='upper center', ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.04))
fig.tight_layout(rect=(0, 0, 1, 0.92))
for ext in ['pdf', 'png']:
    fig.savefig(D + f'out/safelab_srk_curves.{ext}', dpi=300, bbox_inches='tight')
print('saved')
