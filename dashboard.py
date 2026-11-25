from pathlib import Path
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="NARIS v1.0 | Offset-adjusted analysis", layout="wide")
st.title("NARIS — Provisional Offset-Adjusted Results")

ROOT = Path("results/naris_v1_offset_adjusted")
DATASET = Path("experiment_data/naris_v1/final_dataset")
summary_path = ROOT / "run_summary.json"
metrics_path = ROOT / "per_trial_metrics.csv"
avail_path = ROOT / "availability.csv"
agg_path = ROOT / "aggregate_metrics.json"
offset_path = ROOT / "timestamp_offset_diagnostics.csv"
if not summary_path.exists() or not metrics_path.exists():
    st.error("Offset-adjusted results not found. Run naris_offset_adjustment.py first.")
    st.stop()
summary = json.loads(summary_path.read_text(encoding="utf-8"))
metrics = pd.read_csv(metrics_path)
avail = pd.read_csv(avail_path) if avail_path.exists() else pd.DataFrame()
offset = pd.read_csv(offset_path) if offset_path.exists() else pd.DataFrame()
for c in ["tp", "fp", "fn"]:
    metrics[c] = pd.to_numeric(metrics[c], errors="coerce").fillna(0)

c1,c2,c3,c4 = st.columns(4)
c1.metric("Trials processed", summary.get("trials_processed", 0))
c2.metric("Evaluated trial–mode rows", summary.get("evaluated_trial_mode_rows", 0))
#c3.metric("Offset applied", f"{summary.get('applied_offset_seconds', 0):.3f} s")
#c4.metric("Offset diagnostic trials", summary.get("offset_diagnostics_trials", 0))

st.header("1. Overall reconstruction statistics")
mode_order = ["host_only", "network_only", "combined"]
def pooled(g):
    tp,fp,fn = g.tp.sum(),g.fp.sum(),g.fn.sum()
    p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0
    return pd.Series({"Trials":g.trial_id.nunique(),"TP":tp,"FP":fp,"FN":fn,"Precision":p,"Recall":r,"F1":2*p*r/(p+r) if p+r else 0,"Completeness":r})
overall = metrics.groupby("mode").apply(pooled, include_groups=False).reindex(mode_order)
st.dataframe(overall.style.format({"Precision":"{:.1%}","Recall":"{:.1%}","F1":"{:.1%}","Completeness":"{:.1%}"}), use_container_width=True)
left,right=st.columns(2)
with left:
    st.subheader("F1-score by reconstruction mode")
    st.bar_chart(overall[["F1"]])
with right:
    st.subheader("Pooled precision and recall")
    st.bar_chart(overall[["Precision","Recall"]])

st.header("2. Performance across degradation levels")
by_level = metrics.groupby(["level","mode"]).apply(pooled, include_groups=False).reset_index()
level_order=[x for x in ["L0","L1","L2","L3","L4"] if x in by_level.level.astype(str).unique()]
f1=by_level.pivot(index="level",columns="mode",values="F1").reindex(level_order)
comp=by_level.pivot(index="level",columns="mode",values="Completeness").reindex(level_order)
st.subheader("F1-score")
st.line_chart(f1)
st.subheader("Reconstruction completeness")
st.line_chart(comp)

st.header("3. Timestamp-offset diagnostic")
if not offset.empty:
    st.write({"Mean raw offset (s)": summary.get("observed_raw_offset_mean_seconds"), "Minimum (s)": summary.get("observed_raw_offset_min_seconds"), "Maximum (s)": summary.get("observed_raw_offset_max_seconds"), "Mean residual after applied offset (s)": summary.get("residual_mean_seconds")})
    st.dataframe(offset, hide_index=True, use_container_width=True)
else:
    st.info("No matched raw network/ground-truth transfer timestamp pairs were found.")

st.header("4. Inspect an adjusted trial")
trial_ids=sorted(metrics.trial_id.dropna().unique().tolist())
trial=st.selectbox("Trial ID",trial_ids)
rows=metrics[metrics.trial_id==trial].copy()
st.dataframe(rows[[c for c in ["level","mode","predicted_events","ground_truth_events","tp","fp","fn","precision","recall","f1","mean_timestamp_error_seconds","event_order_accuracy","evidence_coverage"] if c in rows.columns]],hide_index=True,use_container_width=True)
mode=st.selectbox("Adjusted reconstructed timeline",mode_order)
timeline=DATASET/trial/"reconstruction_offset_adjusted"/mode/"reconstructed_timeline.json"
if timeline.exists():
    payload=json.loads(timeline.read_text(encoding="utf-8"))
    st.caption(f"{payload.get('event_count',0)} events · {payload.get('timestamp_adjustment',{}).get('status','unknown')}")
    ev=pd.json_normalize(payload.get("events",[]))
    cols=[c for c in ["timestamp","timestamp_raw_pcap","action","host","evidence_source","corroborated_by_network","timestamp_adjustment_seconds"] if c in ev.columns]
    st.dataframe(ev[cols],hide_index=True,use_container_width=True)
    st.download_button("Download adjusted timeline JSON",json.dumps(payload,indent=2),f"{trial}_{mode}_adjusted_timeline.json","application/json")
else:
    st.info("No adjusted timeline exists for this trial/mode.")

st.header("5. Download results")
for label,path,mime in [
    ("Per-trial metrics CSV",metrics_path,"text/csv"),
    ("Offset diagnostics CSV",offset_path,"text/csv"),
    ("Availability CSV",avail_path,"text/csv"),
    ("Aggregate metrics JSON",agg_path,"application/json"),
    ("Run summary JSON",summary_path,"application/json"),
]:
    if path.exists():
        st.download_button(label,path.read_bytes(),path.name,mime)

st.caption("Raw results remain in results/naris_v1. Adjusted timelines are stored separately under reconstruction_offset_adjusted.")
st.warning("Sensitivity-analysis view only: network timestamps are shifted by the empirically estimated 663.389 s. This is not yet a validated clock correction. Raw evidence and raw results remain unchanged.")
