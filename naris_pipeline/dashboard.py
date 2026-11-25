import json
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title='NARIS v1.0 Evaluation Dashboard', layout='wide')
st.title('NARIS v1.0 — Reconstruction & Evaluation Dashboard')
st.caption('Evidence-backed outputs only. Ground truth is used for evaluation, not reconstruction.')
root=Path('results/naris_v1')
summary_path=root/'run_summary.json'
if not summary_path.exists():
    st.warning('Run run_naris_reconstruction.py first. Expected results/naris_v1/run_summary.json.')
    st.stop()
summary=json.loads(summary_path.read_text())
a,b,c=st.columns(3)
a.metric('Reconstruction outputs',summary.get('generated_reconstruction_outputs',0))
b.metric('Evaluated trial-mode rows',summary.get('evaluated_trial_mode_rows',0))
c.metric('Availability records',summary.get('availability_rows',0))
metrics_path=root/'per_trial_metrics.csv'
if metrics_path.exists():
    df=pd.read_csv(metrics_path)
    st.subheader('Performance by reconstruction mode')
    agg=df.groupby('mode').agg(Trials=('trial_id','nunique'),Precision=('precision','mean'),Recall=('recall','mean'),F1=('f1','mean'),Completeness=('reconstruction_completeness','mean'),Evidence_Coverage=('evidence_coverage','mean')).reset_index()
    st.dataframe(agg, use_container_width=True)
    st.bar_chart(agg.set_index('mode')[['Precision','Recall','F1']])
    st.subheader('Performance by degradation level')
    lev=df.groupby(['level','mode'])[['precision','recall','f1','reconstruction_completeness','evidence_coverage']].mean().reset_index()
    st.dataframe(lev, use_container_width=True)
    st.subheader('Per-trial metrics')
    st.dataframe(df, use_container_width=True)
    st.download_button('Download per-trial metrics CSV',df.to_csv(index=False),'per_trial_metrics.csv','text/csv')
else: st.info('No evaluated rows were generated.')
avail_path=root/'availability.csv'
if avail_path.exists():
    av=pd.read_csv(avail_path)
    st.subheader('Evidence and mode availability')
    st.dataframe(av, use_container_width=True)
    st.download_button('Download availability CSV',av.to_csv(index=False),'availability.csv','text/csv')
agg=root/'aggregate_metrics.json'
if agg.exists():
    st.subheader('Pooled aggregate metrics')
    st.json(json.loads(agg.read_text()))
