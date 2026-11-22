
import argparse
import json
import sys

from pathlib import Path

from src.naris_gt.ground_truth import (
    DATASET_ROOT,
    GroundTruthError,
    GroundTruthRecorder,
    validate_timestamp,
)


EXPECTED_ACTIONS = [
    "create_test_script",
    "execute_test_process",
    "create_persistence_artifact",
    "verify_persistence_artifact",
]

EXPECTED_SOURCE_IP = "192.168.57.20"
EXPECTED_HOST = "NARIS-WIN"


def load_source_log(source_path):
    source_path = Path(source_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"S2 execution log not found: {source_path}"
        )

    try:
        data = json.loads(
            source_path.read_text(encoding="utf-8-sig")
        )
    except (json.JSONDecodeError, OSError) as error:
        raise GroundTruthError(
            f"Could not read S2 execution log: {error}"
        ) from error

    if not isinstance(data, dict):
        raise GroundTruthError(
            "A trial-bound transfer envelope is required."
        )

    if data.get("source_ip") != EXPECTED_SOURCE_IP:
        raise GroundTruthError("Unexpected transfer source IP.")

    events = data.get("events")

    if not isinstance(events, list) or len(events) != 4:
        raise GroundTruthError("Expected exactly four S2 events.")

    if data.get("event_count") != len(events):
        raise GroundTruthError("Transfer event count mismatch.")

    return data


def validate_source_log(data, trial_id):
    if data.get("trial_id") != trial_id:
        raise GroundTruthError(
            "Received log belongs to a different trial."
        )

    if data.get("scenario_id") != "S2":
        raise GroundTruthError("Source scenario is not S2.")

    if data.get("degradation_level_id") != "L0":
        raise GroundTruthError("Only L0 imports are currently permitted.")

    events = data["events"]
    run_ids = set()
    source_ids = set()

    required = [
        "event_id",
        "experiment_id",
        "scenario_id",
        "degradation_level_id",
        "run_id",
        "sequence",
        "timestamp",
        "action",
        "host",
        "process",
        "resource",
        "outcome",
        "details",
    ]

    for sequence, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            raise GroundTruthError("Invalid event record.")

        if any(field not in event for field in required):
            raise GroundTruthError(
                f"Event {sequence} is missing required fields."
            )

        if event["experiment_id"] != trial_id:
            raise GroundTruthError("Event trial ID mismatch.")

        if event["scenario_id"] != "S2":
            raise GroundTruthError("Event scenario mismatch.")

        if event["degradation_level_id"] != "L0":
            raise GroundTruthError("Event degradation mismatch.")

        if event["sequence"] != sequence:
            raise GroundTruthError("Invalid event sequence.")

        if event["outcome"] != "success":
            raise GroundTruthError(
                "Failed or partial executions cannot be imported "
                "as successful trials."
            )

        if event["host"] != EXPECTED_HOST:
            raise GroundTruthError("Unexpected execution host.")

        if not isinstance(event["process"], dict):
            raise GroundTruthError("Invalid process record.")

        if not isinstance(event["resource"], dict):
            raise GroundTruthError("Invalid resource record.")

        if not isinstance(event["details"], dict):
            raise GroundTruthError("Invalid event details.")

        if not isinstance(event["event_id"], str):
            raise GroundTruthError("Invalid source event ID.")

        if event["event_id"] in source_ids:
            raise GroundTruthError("Duplicate source event ID.")

        source_ids.add(event["event_id"])
        run_ids.add(event["run_id"])

        validate_timestamp(event["timestamp"])

    if len(run_ids) != 1:
        raise GroundTruthError(
            "Events do not belong to one execution run."
        )

    run_id = next(iter(run_ids))

    if data.get("run_id") != run_id:
        raise GroundTruthError("Transfer run ID mismatch.")

    if [event["action"] for event in events] != EXPECTED_ACTIONS:
        raise GroundTruthError("Invalid S2 action sequence.")

    return events, run_id


def import_s2_events(source_path, trial_id):
    if not trial_id or Path(trial_id).name != trial_id:
        raise GroundTruthError("Invalid trial ID.")

    recorder = GroundTruthRecorder(DATASET_ROOT / trial_id)

    if recorder.scenario_id != "S2":
        raise GroundTruthError("Destination trial is not S2.")

    if recorder.config.get("degradation_level_id") != "L0":
        raise GroundTruthError("Destination trial is not L0.")

    data = load_source_log(source_path)
    events, run_id = validate_source_log(data, trial_id)

    existing = recorder._load_event_store()

    existing_source_ids = {
        event.get("details", {}).get("source_event_id")
        for event in existing["events"]
    }

    incoming_ids = {event["event_id"] for event in events}

    if existing_source_ids.intersection(incoming_ids):
        raise GroundTruthError(
            "Source events have already been imported."
        )

    if existing["event_count"] != 0:
        raise GroundTruthError(
            "Destination trial already contains ground-truth events."
        )

    imported = []

    for source in events:
        imported.append(
            recorder.record_event(
                action=source["action"],
                host=source["host"],
                outcome=source["outcome"],
                process=source["process"],
                resource=source["resource"],
                details={
                    **source["details"],
                    "source_event_id": source["event_id"],
                    "source_run_id": run_id,
                    "source_sequence": source["sequence"],
                    "source_log": "s2_raw_events.json",
                },
                timestamp=source["timestamp"],
            )
        )

    final_store = recorder._load_event_store()

    return {
        "trial_id": trial_id,
        "run_id": run_id,
        "imported_events": len(imported),
        "total_ground_truth_events": final_store["event_count"],
        "hash_chain_valid": GroundTruthRecorder.verify_event_chain(
            final_store["events"]
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--trial-id", required=True)
    args = parser.parse_args()

    try:
        result = import_s2_events(args.source, args.trial_id)

        print("\nNARIS TRIAL-AWARE S2 IMPORT")
        print("-" * 42)

        for key, value in result.items():
            print(f"{key}: {value}")

        print("Import completed.")

    except (GroundTruthError, FileNotFoundError, OSError) as error:
        print(f"IMPORT FAILED: {error}", file=sys.stderr)
        sys.exit(1)
