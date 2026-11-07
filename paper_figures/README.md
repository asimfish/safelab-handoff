# SafeLab Table 2 + SR@k curves: reproduction

Inputs
- `data.json`: snapshot of https://asimfish.github.io/safelab-handoff/data.json taken 2026-11-07 ~10:00 UTC (749 evaluations). SHA-256 in `DATA_JSON_SHA256.txt`.
- `agent_reported_cells.json`: cells that are not yet in data.json (π0.5 3-subtask 40k; π0.5/MemoryVLA 10-subtask from the validated stage-10 report, v11 block; π0.5 5-subtask phase counts; Mem-0 7-subtask h4). Each entry names its source.

Rule
- Oracle: SafeLab-Eval-v1.1 placement, no grasp assistance, fixed scenes.
- Cell value = mean over execution horizons h=4 and h=8 of success/trials (all seeds pooled within a horizon). Infrastructure-error episodes stay in the denominator as failures.
- SR@k = episodes whose v1.1 phase count is >= k, divided by all episodes; averaged over horizons that have phase histograms.
- Avg = unweighted mean over 3/5/7/10 when all four exist.

Run
```
python3 compute_table2.py extra      # prints Table 2 + SR@k, writes out/table2_srk.json and out/srk.csv
python3 plot_srk.py                  # needs matplotlib; writes out/safelab_srk_curves.pdf/.png
```
The row IDs used for every cell are listed in `compute_table2.py` (SEL) and `out/SOURCES.md`.
