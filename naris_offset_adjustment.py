#!/usr/bin/env python3
"""Create a separate provisional offset-adjusted NARIS evaluation.

Original evidence and original reconstruction outputs are never overwritten.
The empirical offset is a sensitivity-analysis parameter, not a validated clock correction.
"""
from __future__ import annotations
import argparse, csv, json, math, statistics, shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

DEFAULT_OFFSET = 663.389
MODES = ("host_only", "network_only", "combined")


def read_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def iso_from_epoch(value):
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def adjust_network_events(events, offset):
    out = []
    for event in events:
        e = dict(event)
        if e.get("evidence_source") == "pcap_http_post" and e.get("timestamp"):
            epoch = parse_ts(e["timestamp"])
            if epoch is not None:
                e["timestamp_raw_pcap"] = e["timestamp"]
                e["timestamp"] = iso_from_epoch(epoch - offset)
                e["timestamp_adjustment_seconds"] = offset
                e["timestamp_adjustment_status"] = "provisional_empirical_offset"
        out.append(e)
    return out


def merge_combined(host_events, network_events, dedup_seconds=1.0):
    merged = [dict(e) for e in host_events]
    for net in network_events:
        nt = parse_ts(net.get("timestamp"))
        duplicate = False
        for host in merged:
            if host.get("action") != net.get("action"):
                continue
            ht = parse_ts(host.get("timestamp"))
            if ht is not None and nt is not None and abs(ht - nt) <= dedup_seconds:
                host["corroborated_by_network"] = True
                host["network_timestamp_raw_pcap"] = net.get("timestamp_raw_pcap")
                host["network_timestamp_adjustment_seconds"] = net.get("timestamp_adjustment_seconds")
                duplicate = True
                break
        if not duplicate:
            merged.append(dict(net))
    merged.sort(key=lambda e: (parse_ts(e.get("timestamp")) is None, parse_ts(e.get("timestamp")) or 0))
    return merged


def evaluate(pred, truth, tolerance=10.0):
    remaining = set(range(len(truth)))
    matches = []
    ordered_pred = sorted(pred, key=lambda x: parse_ts(x.get("timestamp")) or 0)
    for p in ordered_pred:
        pts = parse_ts(p.get("timestamp"))
        candidates = []
        for ti in remaining:
            t = truth[ti]
            if p.get("action") != t.get("action"):
                continue
            tts = parse_ts(t.get("timestamp"))
            delta = abs(pts - tts) if pts is not None and tts is not None else None
            if delta is None or delta <= tolerance:
                candidates.append((delta if delta is not None else float("inf"), ti, delta))
        if candidates:
            _, ti, delta = min(candidates)
            remaining.remove(ti)
            matches.append((p, truth[ti], delta))
    tp = len(matches); fp = max(0, len(pred) - tp); fn = max(0, len(truth) - tp)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    errors = [m[2] for m in matches if m[2] is not None]
    ordered = [(parse_ts(p.get("timestamp")), int(t.get("sequence", 0))) for p, t, _ in matches]
    pair_ok = pair_total = 0
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            if ordered[i][0] is None or ordered[j][0] is None:
                continue
            pair_total += 1
            if (ordered[i][0] < ordered[j][0]) == (ordered[i][1] < ordered[j][1]):
                pair_ok += 1
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "reconstruction_completeness": recall,
        "mean_timestamp_error_seconds": statistics.mean(errors) if errors else None,
        "median_timestamp_error_seconds": statistics.median(errors) if errors else None,
        "event_order_accuracy": pair_ok / pair_total if pair_total else None,
        "evidence_coverage": tp / len(truth) if truth else 0.0,
    }


def pooled(rows):
    tp = sum(r["tp"] for r in rows); fp = sum(r["fp"] for r in rows); fn = sum(r["fn"] for r in rows)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    errs = [x["mean_timestamp_error_seconds"] for x in rows if x.get("mean_timestamp_error_seconds") is not None]
    orders = [x["event_order_accuracy"] for x in rows if x.get("event_order_accuracy") is not None]
    return {
        "trials": len({x["trial_id"] for x in rows}), "TP": tp, "FP": fp, "FN": fn,
        "precision": p, "recall": r, "f1": 2*p*r/(p+r) if p+r else 0.0,
        "completeness": r,
        "mean_trial_timestamp_error_seconds": statistics.mean(errs) if errs else None,
        "mean_trial_event_order_accuracy": statistics.mean(orders) if orders else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("experiment_data/naris_v1/final_dataset"))
    ap.add_argument("--output", type=Path, default=Path("results/naris_v1_offset_adjusted"))
    ap.add_argument("--offset-seconds", type=float, default=DEFAULT_OFFSET)
    ap.add_argument("--tolerance-seconds", type=float, default=10.0)
    args = ap.parse_args()
    dataset = args.dataset.resolve(); outroot = args.output.resolve()
    timeline_root_name = "reconstruction_offset_adjusted"
    outroot.mkdir(parents=True, exist_ok=True)
    rows, availability, offset_rows = [], [], []
    generated = 0; processed = 0

    for td in sorted(dataset.iterdir()):
        if not td.is_dir():
            continue
        original_gt = td / "evidence" / "host" / "original" / "execution_envelope.json"
        if not original_gt.is_file():
            continue
        gt_data = read_json(original_gt)
        truth = gt_data.get("events", [])
        if not truth:
            continue
        # Reuse the already-generated, evidence-derived host and network timelines.
        base = td / "reconstruction"
        host_path = base / "host_only" / "reconstructed_timeline.json"
        net_path = base / "network_only" / "reconstructed_timeline.json"
        if not host_path.is_file() and not net_path.is_file():
            continue
        host_payload = read_json(host_path) if host_path.is_file() else {"events": []}
        net_payload = read_json(net_path) if net_path.is_file() else {"events": []}
        host_events = host_payload.get("events", [])
        raw_network = net_payload.get("events", [])
        adjusted_network = adjust_network_events(raw_network, args.offset_seconds)
        combined = merge_combined(host_events, adjusted_network)
        mode_events = {
            "host_only": host_events,
            "network_only": adjusted_network,
            "combined": combined,
        }
        level = gt_data.get("degradation_level_id", "unknown")
        processed += 1

        # Per-trial raw-vs-adjusted timestamp diagnostic for network transfer events.
        gt_transfer = next((e for e in truth if e.get("action") == "transfer_file"), None)
        net_transfer = next((e for e in raw_network if e.get("action") == "transfer_file"), None)
        if gt_transfer and net_transfer:
            raw_delta = None
            gt_epoch = parse_ts(gt_transfer.get("timestamp")); raw_epoch = parse_ts(net_transfer.get("timestamp"))
            if gt_epoch is not None and raw_epoch is not None:
                raw_delta = raw_epoch - gt_epoch
            offset_rows.append({
                "trial_id": td.name, "level": level,
                "ground_truth_transfer_timestamp": gt_transfer.get("timestamp"),
                "raw_pcap_transfer_timestamp": net_transfer.get("timestamp"),
                "raw_offset_seconds": raw_delta,
                "applied_offset_seconds": args.offset_seconds,
                "residual_after_adjustment_seconds": (raw_delta - args.offset_seconds) if raw_delta is not None else None,
            })

        for mode, events in mode_events.items():
            status = "ok" if events else "no_events_available"
            availability.append({"trial_id": td.name, "level": level, "mode": mode, "status": status, "events": len(events)})
            if not events:
                continue
            payload = {
                "trial_id": td.name,
                "scenario_id": gt_data.get("scenario_id", "S1"),
                "degradation_level_id": level,
                "reconstruction_mode": mode,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "event_count": len(events), "events": events,
                "ground_truth_used_for_reconstruction": False,
                "timestamp_adjustment": {
                    "status": "provisional_sensitivity_analysis" if mode != "host_only" else "not_applied",
                    "method": "subtract fixed empirically estimated offset from pcap_http_post event timestamps",
                    "offset_seconds": args.offset_seconds if mode != "host_only" else 0.0,
                    "raw_evidence_preserved": True,
                },
            }
            target = td / timeline_root_name / mode / "reconstructed_timeline.json"
            write_json(target, payload); generated += 1
            met = evaluate(events, truth, args.tolerance_seconds)
            rows.append({"trial_id": td.name, "level": level, "mode": mode,
                         "predicted_events": len(events), "ground_truth_events": len(truth), **met})

    if not rows:
        raise SystemExit(f"No usable trials found. Expected original envelopes under {dataset}/<trial>/evidence/host/original/execution_envelope.json and existing reconstruction timelines under reconstruction/<mode>/.")

    def write_csv(path, data):
        keys = sorted({k for row in data for k in row})
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(data)

    write_csv(outroot / "per_trial_metrics.csv", rows)
    write_csv(outroot / "availability.csv", availability)
    write_csv(outroot / "timestamp_offset_diagnostics.csv", offset_rows)
    agg = []
    for mode in MODES:
        group = [r for r in rows if r["mode"] == mode]
        if group:
            agg.append({"mode": mode, **pooled(group)})
    by_level = []
    for level in sorted({r["level"] for r in rows}):
        for mode in MODES:
            group = [r for r in rows if r["level"] == level and r["mode"] == mode]
            if group:
                by_level.append({"level": level, "mode": mode, **pooled(group)})
    write_json(outroot / "aggregate_metrics.json", agg)
    write_csv(outroot / "level_mode_statistics.csv", by_level)

    deltas = [r["raw_offset_seconds"] for r in offset_rows if r["raw_offset_seconds"] is not None]
    summary = {
        "dataset": str(dataset), "trials_processed": processed,
        "generated_adjusted_timeline_outputs": generated,
        "evaluated_trial_mode_rows": len(rows),
        "applied_offset_seconds": args.offset_seconds,
        "offset_diagnostics_trials": len(deltas),
        "observed_raw_offset_mean_seconds": statistics.mean(deltas) if deltas else None,
        "observed_raw_offset_min_seconds": min(deltas) if deltas else None,
        "observed_raw_offset_max_seconds": max(deltas) if deltas else None,
        "residual_mean_seconds": statistics.mean([d-args.offset_seconds for d in deltas]) if deltas else None,
        "ground_truth_used_for_reconstruction": False,
        "interpretation": "Provisional offset-adjusted sensitivity analysis. Original PCAPs, original timelines, and raw results are preserved. The offset is not yet a validated clock correction.",
        "adjusted_timeline_directory": timeline_root_name,
    }
    write_json(outroot / "run_summary.json", summary)
    print(json.dumps(summary, indent=2))
    print(f"Adjusted results: {outroot}")
    print(f"Adjusted timelines: {dataset / '<trial-id>' / timeline_root_name}")

if __name__ == "__main__":
    main()
