Validated CPU first version: v1.3 follows the explicit user clarification that measured target-support contact is authoritative. Historical protocol rows are preserved.

|Method|Protocol|S / 100|Unknown|Half-task confirmed /100|Mean completed (known n)|
|---|---|---:|---:|---:|---:|
|mem0_30k_h8|strict|0|5|26|2.136842105263158 (n=95, N=7)|
|mem0_30k_h8|v1.1|5|0|26|2.38 (n=100, N=7)|
|mem0_30k_h8|v1.2-relaxed|5|0|28|2.59 (n=100, N=7)|
|mem0_30k_h8|v1.3-lenient|5|0|33|1.5 (n=100, N=4)|
|ours_aligned_30k_h8|strict|0|8|35|2.3260869565217392 (n=92, N=7)|
|ours_aligned_30k_h8|v1.1|7|1|35|2.686868686868687 (n=99, N=7)|
|ours_aligned_30k_h8|v1.2-relaxed|11|6|38|2.904255319148936 (n=94, N=7)|
|ours_aligned_30k_h8|v1.3-lenient|11|1|45|1.8181818181818181 (n=99, N=4)|
|pi05_40k_h4|strict|0|0|0|0.03 (n=100, N=7)|
|pi05_40k_h4|v1.1|0|0|0|0.03 (n=100, N=7)|
|pi05_40k_h4|v1.2-relaxed|0|0|0|0.03 (n=100, N=7)|
|pi05_40k_h4|v1.3-lenient|0|0|0|0.05 (n=100, N=4)|
|pi05_40k_h8|strict|0|14|0|0.45348837209302323 (n=86, N=7)|
|pi05_40k_h8|v1.1|0|14|0|0.45348837209302323 (n=86, N=7)|
|pi05_40k_h8|v1.2-relaxed|0|14|0|0.46511627906976744 (n=86, N=7)|
|pi05_40k_h8|v1.3-lenient|0|14|1|0.7325581395348837 (n=86, N=4)|

v1.3 N=4 distinct cups each on the weighing pan. Historical protocols N=7 ordered subtasks. Initial pads receive no credit.

Measured-support validation: 10/10 expert paths passed (3 unique raw traces); all 15 real negative windows rejected. Height-only suspended cases are rejected even inside the nominal 15mm band. Same parameters for all methods. Literal OR-height draft retained separately and not published as accepted.
No new simulator, model, control or original strict/v1.1/v1.2 change. V1.3 counts four distinct cups; original admission and execution-chain limitations remain explicit.

Full SR@k, Wilson intervals, paired/bootstrap intervals and left/right splits are in FIRST_FOUR_PROTOCOL_TABLE.json.
