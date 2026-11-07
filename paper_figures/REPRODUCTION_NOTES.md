# Reproduce the final paper panel offline

The complete, pinned 749-evaluation input ships in this directory as `data.json.gz` (gzip level 9). There is no required external input download. Both author-supplied compute scripts prefer an adjacent `data.json` if present, otherwise read `data.json.gz` directly. The supplied plot_two.py and plot_len.py use paths relative to their own directory.

From this directory:

    python3 compute_table2_v12best.py
    python3 compute_table2.py extra
    python3 plot_srk.py
    python3 plot_two.py
    python3 plot_len.py

Matplotlib is required only for the three plotting commands. The two compute commands use the Python standard library. `out/` is included in the reproduction bundle.

The optional verified entry runs the full reproduction:

    python3 reproduce.py
    python3 reproduce.py --no-plots

It verifies both compressed and decoded byte counts and SHA256 against INPUT_MANIFEST.json, checks the strict table, the three-setting main Avg and the four-setting full-table Avg against frozen-data.json, and leaves no expanded data.json behind. It produces legacy strict-reference curves and CSV. The supplemental portable_plot_two.py uses the rounded final two-method display arrays without changing the supplied scripts.

Snapshot identity:
- gzip bytes: 292423
- gzip SHA256: e0e43f3d8d3693527806247d6dbe8d39dcf72f5498ce5eafb7ba681055e285b5
- decoded bytes: 5898454
- decoded SHA256: b5d444842545051dddca696d4a8c87c5c0984547c8f29785443fbe8df91ccd99

The gzip input is the single requested exception to the 200KB per-file guidance: it replaces the full 5.9MB snapshot without splitting it into external inputs. The TOS URL in INPUT_MANIFEST.json is an optional byte-identical backup only. The root dashboard data.json is unchanged.

The main table uses v1.2-relaxed / best of h4,h8. Final progress figures use v1.1 / mean horizons. out/srk.csv and safelab_srk_curves.pdf contain historical strict-reference outputs including the supplied π0.5 phase distributions. π0.5 3-subtask SR@3 can exceed episode success (3.5 vs. 2.0) because final hold/safety conditions can fail. Only MemoryVLA task 7 lacks an evaluated curve.
