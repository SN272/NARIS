NARIS v1.0 RECONSTRUCTION & EVALUATION PIPELINE

1. Copy run_naris_reconstruction.py and dashboard.py into the NARIS-Research repository root.
2. Open PowerShell in D:\NARIS\NARIS-Research.
3. Install dependency:
      py -m pip install scapy pandas streamlit
4. Run reconstruction/evaluation:
      py run_naris_reconstruction.py --dataset experiment_data\naris_v1\final_dataset --output results\naris_v1
5. Launch dashboard:
      py -m streamlit run dashboard.py

Outputs:
  results/naris_v1/run_summary.json
  results/naris_v1/availability.csv
  results/naris_v1/per_trial_metrics.csv
  results/naris_v1/aggregate_metrics.json
  Each successful timeline is saved under:
  experiment_data/naris_v1/final_dataset/<trial-id>/reconstruction/<mode>/reconstructed_timeline.json

Important methodological constraints:
- The reconstruction functions read only degraded host evidence and per-trial PCAPs.
- ground_truth/events.json is opened only in the evaluation phase.
- Missing evidence means no fabricated timeline; the mode is recorded as unavailable.
- Network reconstruction is deliberately conservative: it recognizes HTTP POST requests to the S1 receiver and maps them to transfer_file observations. It does not claim to reconstruct host-side file creation/access/staging from network packets.
- Event matching uses action equality and a 10-second default timestamp tolerance. Report this tolerance in the methodology.
- This is a first executable pipeline. Inspect network_only outputs and verify the HTTP parser against packet captures before claiming final network metrics.
