# Portable reproduction of the final paper panel

The supplied README.md, compute_table2.py, plot_srk.py, compute_table2_v12best.py and plot_two.py are retained verbatim. The last script's original author-specific absolute D path is intentionally not edited.

From this directory, with matplotlib installed:

    python3 reproduce.py

For data and table verification without plotting dependencies:

    python3 reproduce.py --no-plots

The entry downloads the exact 749-evaluation snapshot as local `data.json`, verifies its byte count and SHA256 from INPUT_MANIFEST.json, then executes the unchanged calculation scripts. It verifies BOTH the three-setting main Avg and the four-setting full-table Avg against frozen-data.json. It also produces the legacy strict-reference curves and CSV.

`portable_plot_two.py` executes the unchanged supplied plot source with only its process-local D assignment relocated to an owned temporary directory. It uses the frozen final two-method arrays, writes the final 3/7, all-length and task-10 PDF/PNG files into out/, and never writes the source author's /tmp path. Original source bytes are preserved.

The snapshot is 5,898,454 bytes (SHA256 b5d444842545051dddca696d4a8c87c5c0984547c8f29785443fbe8df91ccd99). To keep the published site within its 35MB cap, it is archived byte-for-byte on public TOS rather than duplicated into the GitHub publication tree. INPUT_MANIFEST.json has the direct anonymous-download URL; reproduce.py creates the requested adjacent data.json locally. The repository ignores that local cache.

The main table is v1.2-relaxed / best of h4,h8; final progress figures are v1.1 / mean horizons. out/srk.csv and safelab_srk_curves.pdf are historical strict-reference outputs containing the subsequently supplied π0.5 phase distributions. π0.5 3-subtask SR@3 can exceed episode success (3.5 vs. 2.0) because final hold/safety conditions can fail. Only MemoryVLA task 7 lacks an evaluated curve.
