NARIS v1.0 — PROVISIONAL OFFSET-ADJUSTED ANALYSIS PACKAGE

Purpose
Create a separate sensitivity-analysis result set using a fixed empirical PCAP timestamp offset of 663.389 seconds. This is for provisional graphs/statistics only. It does NOT establish the cause of the discrepancy and must not replace raw results in the paper.

Safety / preservation
- Original PCAPs are not changed.
- Existing reconstruction/<mode>/ timelines are read only.
- New timelines are written to reconstruction_offset_adjusted/<mode>/.
- Existing results/naris_v1 is not overwritten.
- New results are written to results/naris_v1_offset_adjusted/.

Install dependencies (Windows PowerShell, from D:\NARIS\NARIS-Research)
  py -m pip install pandas matplotlib streamlit

Run the adjusted analysis
  py naris_offset_adjustment.py --dataset experiment_data\naris_v1\final_dataset --output results\naris_v1_offset_adjusted --offset-seconds 663.389

Export publication figures (PNG 300 dpi + PDF)
  py export_naris_figures.py

Launch the adjusted dashboard
  py -m streamlit run dashboard.py

Files
- naris_offset_adjustment.py: reads original execution_envelope.json for evaluation truth and existing evidence-derived reconstruction timelines; applies the offset only to pcap_http_post events; rebuilds combined timelines with 1-second deduplication; evaluates all modes.
- dashboard.py: dashboard for adjusted results; includes metrics, level comparisons, timestamp offset diagnostics, timeline inspection and downloads.
- export_naris_figures.py: creates PNG/PDF graphs and CSV statistics under results/naris_v1_offset_adjusted/report_figures/.

Interpretation
The offset (663.389 s) is an empirically estimated fixed shift. Since it is estimated from the same trial set, adjusted timestamp error is descriptive/sensitivity analysis and is not independent validation. Retain raw results as the primary evidence until the timing issue is debugged.

Expected dataset structure
<dataset>/<trial-id>/evidence/host/original/execution_envelope.json
<dataset>/<trial-id>/reconstruction/host_only/reconstructed_timeline.json
<dataset>/<trial-id>/reconstruction/network_only/reconstructed_timeline.json

If the current dataset uses a different reconstruction path/schema, stop and share the error rather than changing original files.
