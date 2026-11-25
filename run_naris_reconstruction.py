#!/usr/bin/env python3
"""NARIS v1.0 conservative evidence-driven reconstruction and evaluation.
Ground truth is read only in the evaluation phase, never by reconstruction functions.
Requires: pip install scapy
"""
from __future__ import annotations
import argparse, csv, json, re, statistics
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ACTIONS = {"create_test_file", "access_file", "read_file", "stage_file_transfer", "transfer_file"}


def read_json(p):
    with p.open('r', encoding='utf-8-sig') as f: return json.load(f)

def iso_from_epoch(v):
    return datetime.fromtimestamp(float(v), timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')

def norm_event(e, source):
    return {
        "action": e.get("action", "unknown"),
        "timestamp": e.get("timestamp"),
        "host": e.get("host", "unknown"),
        "process": e.get("process", {}),
        "resource": e.get("resource", {}),
        "outcome": e.get("outcome", "unknown"),
        "evidence_source": source,
        "source_sequence": e.get("sequence"),
    }

def reconstruct_host(trial_dir):
    # Host evidence only. Never open ground_truth here.
    candidates = [trial_dir/'evidence'/'host'/'degraded'/'execution_envelope.json',
                  trial_dir/'evidence'/'host'/'degraded'/'events.json']
    p = next((x for x in candidates if x.is_file()), None)
    if not p: return [], "missing_degraded_host_envelope"
    data = read_json(p)
    events = data.get('events', [])
    out = [norm_event(e, 'host_degraded_envelope') for e in events if e.get('action') in ACTIONS]
    return out, ("ok" if out else "host_envelope_has_no_recognized_events")

def reconstruct_network(trial_dir):
    # Conservative network-only inference: recognize an HTTP POST to the lab receiver.
    pcap = trial_dir/'evidence'/'network'/f"s1_{trial_dir.name}.pcap"
    if not pcap.is_file(): return [], "missing_pcap"
    try:
        from scapy.all import rdpcap, TCP, Raw, IP
    except Exception as ex:
        return [], f"scapy_unavailable:{type(ex).__name__}"
    try: packets = rdpcap(str(pcap))
    except Exception as ex: return [], f"pcap_read_error:{type(ex).__name__}"
    streams = defaultdict(list)
    for pkt in packets:
        if TCP in pkt and Raw in pkt:
            ip_src = pkt[IP].src if IP in pkt else ""
            ip_dst = pkt[IP].dst if IP in pkt else ""
            key = (ip_src, int(pkt[TCP].sport), ip_dst, int(pkt[TCP].dport))
            streams[key].append((float(pkt.time), int(pkt[TCP].seq), bytes(pkt[Raw].load)))
    found = []
    for key, chunks in streams.items():
        chunks.sort(key=lambda x: (x[0], x[1]))
        blob = b''.join(x[2] for x in chunks)
        # Search only request headers; don't infer host-side actions from packet payload.
        m = re.search(rb'(?im)^POST\s+([^\s]+)\s+HTTP/1\.[01]', blob)
        if not m: continue
        path = m.group(1).decode('latin1', 'replace')
        if 's1-upload' not in path.lower(): continue
        first_time = chunks[0][0]
        headers = blob.split(b'\r\n\r\n', 1)[0].decode('latin1', 'replace')
        filename = None
        fm = re.search(r'(?i)filename="?([^";\r\n]+)', headers)
        if fm: filename = fm.group(1).strip()
        found.append({
            "action": "transfer_file", "timestamp": iso_from_epoch(first_time),
            "host": key[0], "process": {},
            "resource": {"destination": f"{key[2]}:{key[3]}{path}", "filename": filename},
            "outcome": "observed", "evidence_source": "pcap_http_post",
            "source_sequence": None
        })
    # One observed upload per distinct request/flow, stable ordering.
    found.sort(key=lambda e: e['timestamp'] or '')
    return found, ("ok" if found else "no_matching_http_post_observed")

def parse_ts(s):
    if not s: return None
    try: return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
    except Exception: return None

def reconstruct_combined(host, network):
    # Union observations; suppress same-action events within 1 second, retaining both provenance labels.
    out = list(host)
    for n in network:
        nt = parse_ts(n.get('timestamp'))
        duplicate = False
        for h in out:
            if h.get('action') != n.get('action'): continue
            ht = parse_ts(h.get('timestamp'))
            if ht is not None and nt is not None and abs(ht-nt) <= 1.0:
                h['corroborated_by_network'] = True
                duplicate = True
                break
        if not duplicate: out.append(n)
    out.sort(key=lambda e: (parse_ts(e.get('timestamp')) is None, parse_ts(e.get('timestamp')) or 0))
    return out

def evaluate(pred, truth, tolerance=10.0):
    # One-to-one action match, choosing closest timestamp; no ground truth is exposed to reconstruction.
    remaining = set(range(len(truth)))
    matches = []
    for pi, p in enumerate(sorted(pred, key=lambda x: parse_ts(x.get('timestamp')) or 0)):
        pts = parse_ts(p.get('timestamp'))
        candidates = []
        for ti in remaining:
            t = truth[ti]
            if p.get('action') != t.get('action'): continue
            tts = parse_ts(t.get('timestamp'))
            delta = abs(pts-tts) if pts is not None and tts is not None else None
            if delta is None or delta <= tolerance: candidates.append((delta if delta is not None else float('inf'), ti, delta))
        if candidates:
            _, ti, delta = min(candidates)
            remaining.remove(ti)
            matches.append((p, truth[ti], delta))
    tp=len(matches); fp=max(0,len(pred)-tp); fn=max(0,len(truth)-tp)
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    errors=[x[2] for x in matches if x[2] is not None]
    # Pairwise order accuracy over matched events.
    ordered=[]
    for p,t,d in matches:
        ordered.append((parse_ts(p.get('timestamp')), int(t.get('sequence',0))))
    pair_ok=pair_total=0
    for i in range(len(ordered)):
        for j in range(i+1,len(ordered)):
            if ordered[i][0] is None or ordered[j][0] is None: continue
            pair_total += 1
            if (ordered[i][0] < ordered[j][0]) == (ordered[i][1] < ordered[j][1]): pair_ok += 1
    return {"tp":tp,"fp":fp,"fn":fn,"precision":precision,"recall":recall,"f1":f1,
            "reconstruction_completeness":recall,
            "mean_timestamp_error_seconds":statistics.mean(errors) if errors else None,
            "median_timestamp_error_seconds":statistics.median(errors) if errors else None,
            "event_order_accuracy":pair_ok/pair_total if pair_total else None,
            "evidence_coverage":tp/len(truth) if truth else 0.0}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dataset', type=Path, default=Path('experiment_data/naris_v1/final_dataset'))
    ap.add_argument('--output', type=Path, default=Path('results/naris_v1'))
    ap.add_argument('--tolerance-seconds', type=float, default=10.0)
    args=ap.parse_args(); dataset=args.dataset.resolve(); outroot=args.output.resolve()
    outroot.mkdir(parents=True, exist_ok=True)
    rows=[]; availability=[]; generated=0
    for td in sorted(dataset.iterdir()):
        if not td.is_dir() or not (td/'experiment_config.json').is_file(): continue
        cfg=read_json(td/'experiment_config.json')
        if cfg.get('scenario_id') != 'S1': continue
        # Infrastructure validation excluded by metadata role when available.
        meta_path=td/'metadata.json'
        if meta_path.is_file() and read_json(meta_path).get('dataset_role') != 'research_trial': continue
        host, hs = reconstruct_host(td)
        network, ns = reconstruct_network(td)
        modes={"host_only":host, "network_only":network, "combined":reconstruct_combined(host,network)}
        gtpath=td/'ground_truth'/'events.json'
        truth=read_json(gtpath).get('events',[]) if gtpath.is_file() else None
        level=cfg.get('degradation_level_id','unknown')
        for mode, events in modes.items():
            status = hs if mode=='host_only' else ns if mode=='network_only' else ('ok' if host or network else f'host:{hs};network:{ns}')
            if not events:
                availability.append({"trial_id":td.name,"level":level,"mode":mode,"status":status,"events":0})
                continue
            target=td/'reconstruction'/mode
            target.mkdir(parents=True,exist_ok=True)
            payload={"trial_id":td.name,"scenario_id":"S1","degradation_level_id":level,
                     "reconstruction_mode":mode,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
                     "event_count":len(events),"events":events,
                     "ground_truth_used_for_reconstruction":False}
            (target/'reconstructed_timeline.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
            generated+=1
            availability.append({"trial_id":td.name,"level":level,"mode":mode,"status":status,"events":len(events)})
            if truth is not None:
                met=evaluate(events,truth,args.tolerance_seconds)
                rows.append({"trial_id":td.name,"level":level,"mode":mode,"predicted_events":len(events),"ground_truth_events":len(truth),**met})
    fields=sorted({k for r in rows for k in r})
    if rows:
        with (outroot/'per_trial_metrics.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
        # Aggregate by mode and level using pooled counts, not averages of per-trial ratios.
        aggregates=[]
        for mode in sorted({r['mode'] for r in rows}):
            for level in sorted({r['level'] for r in rows}):
                group=[r for r in rows if r['mode']==mode and r['level']==level]
                if not group: continue
                tp=sum(r['tp'] for r in group); fp=sum(r['fp'] for r in group); fn=sum(r['fn'] for r in group)
                pr=tp/(tp+fp) if tp+fp else 0; re=tp/(tp+fn) if tp+fn else 0
                errs=[r['mean_timestamp_error_seconds'] for r in group if r['mean_timestamp_error_seconds'] is not None]
                orders=[r['event_order_accuracy'] for r in group if r['event_order_accuracy'] is not None]
                aggregates.append({"mode":mode,"level":level,"trials_evaluated":len(group),"tp":tp,"fp":fp,"fn":fn,
                    "precision":pr,"recall":re,"f1":2*pr*re/(pr+re) if pr+re else 0,
                    "mean_timestamp_error_seconds":statistics.mean(errs) if errs else None,
                    "mean_event_order_accuracy":statistics.mean(orders) if orders else None})
        (outroot/'aggregate_metrics.json').write_text(json.dumps(aggregates,indent=2),encoding='utf-8')
    with (outroot/'availability.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['trial_id','level','mode','status','events']); w.writeheader(); w.writerows(availability)
    summary={"dataset":str(dataset),"generated_reconstruction_outputs":generated,
             "evaluated_trial_mode_rows":len(rows),"availability_rows":len(availability),
             "ground_truth_used_for_reconstruction":False,
             "note":"Only evidence-backed modes produce timeline files. Missing modes are listed in availability.csv."}
    (outroot/'run_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2)); print('Results:',outroot)
if __name__=='__main__': main()
