
import argparse
import json
import sys

from pathlib import Path

from src.naris_gt.ground_truth import (
    DATASET_ROOT,
    GroundTruthError,
    GroundTruthRecorder,
    validate_timestamp
)


EXPECTED_ACTIONS = [
    "create_test_file",
    "access_file",
    "read_file",
    "stage_file_transfer",
    "transfer_file"
]

EXPECTED_SOURCE_IP = "192.168.56.20"
EXPECTED_HOST = "NARIS-Windows"
ALLOWED_LEVELS = {"L0", "L1", "L2", "L3", "L4"}


def load_source_log(source_path):
    source_path = Path(source_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"S1 execution log not found: {source_path}"
        )

    try:
        data = json.loads(
            source_path.read_text(encoding="utf-8-sig")
        )
    except (json.JSONDecodeError, OSError) as error:
        raise GroundTruthError(
            f"Could not read S1 execution log: {error}"
        ) from error

    if not isinstance(data, dict):
        raise GroundTruthError(
            "A trial-bound transfer envelope is required."
        )

    if data.get("source_ip") != EXPECTED_SOURCE_IP:
        raise GroundTruthError("Unexpected transfer source IP.")

    events = data.get("events")

    if not isinstance(events, list) or len(events) != len(EXPECTED_ACTIONS):
        raise GroundTruthError(
            f"Expected exactly {len(EXPECTED_ACTIONS)} source events."
        )

    if data.get("event_count") != len(events):
        raise GroundTruthError("Transfer event count mismatch.")

    return data


def validate_source_log(data, trial_id, expected_level):
    if data.get("trial_id") != trial_id:
        raise GroundTruthError(
            "Received log belongs to a different trial."
        )

    if data.get("experiment_id") != trial_id:
        raise GroundTruthError(
            "Transfer experiment ID does not match the destination trial."
        )

    if data.get("scenario_id") != "S1":
        raise GroundTruthError("Source scenario is not S1.")

    if data.get("degradation_level_id") not in ALLOWED_LEVELS:
        raise GroundTruthError("Invalid source degradation level.")

    if data.get("degradation_level_id") != expected_level:
        raise GroundTruthError(
            "Source degradation level does not match destination trial."
        )

    events = data["events"]

    run_ids = set()
    source_ids = set()

    for sequence, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            raise GroundTruthError("Invalid event record.")

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
            "details"
        ]

        if any(field not in event for field in required):
            raise GroundTruthError(
                f"Event {sequence} is missing required fields."
            )

        if event["experiment_id"] != trial_id:
            raise GroundTruthError("Event trial ID mismatch.")

        if event["scenario_id"] != "S1":
            raise GroundTruthError("Event scenario mismatch.")

        if event["degradation_level_id"] != expected_level:
            raise GroundTruthError(
                "Event degradation level does not match destination trial."
            )

        if event["run_id"] != data.get("run_id"):
            raise GroundTruthError("Event run ID mismatch.")

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

        event_id = event["event_id"]

        if not isinstance(event_id, str) or not event_id.strip():
            raise GroundTruthError("Invalid source event ID.")

        if event_id in source_ids:
            raise GroundTruthError("Duplicate source event ID.")

        source_ids.add(event_id)
        run_ids.add(event["run_id"])

        validate_timestamp(event["timestamp"])

    if len(run_ids) != 1:
        raise GroundTruthError(
            "Events do not belong to one execution run."
        )

    if data.get("run_id") != next(iter(run_ids)):
        raise GroundTruthError("Transfer run ID mismatch.")

    if [event["action"] for event in events] != EXPECTED_ACTIONS:
        raise GroundTruthError("Invalid S1 action sequence.")

    return events, next(iter(run_ids))


def import_s1_events(source_path, trial_id):
    if (
        not isinstance(trial_id, str)
        or not trial_id
        or Path(trial_id).name != trial_id
    ):
        raise GroundTruthError("Invalid trial ID.")

    recorder = GroundTruthRecorder(DATASET_ROOT / trial_id)

    if recorder.scenario_id != "S1":
        raise GroundTruthError("Destination trial is not S1.")

    config = recorder.config

    if config.get("design_version") != "1.0":
        raise GroundTruthError(
            "Destination trial is not part of NARIS v1.0."
        )

    expected_level = config.get("degradation_level_id")

    if expected_level not in ALLOWED_LEVELS:
        raise GroundTruthError(
            "Destination trial has an invalid degradation level."
        )

    data = load_source_log(source_path)

    events, run_id = validate_source_log(
        data,
        trial_id,
        expected_level
    )

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

    # All source records are validated before the first write.
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
                    "source_log": "s1_raw_events.json",
                    "degradation_level_id": expected_level
                },
                timestamp=source["timestamp"]
            )
        )

    final_store = recorder._load_event_store()

    return {
        "trial_id": trial_id,
        "run_id": run_id,
        "degradation_level_id": expected_level,
        "imported_events": len(imported),
        "total_ground_truth_events": final_store["event_count"],
        "hash_chain_valid": GroundTruthRecorder.verify_event_chain(
            final_store["events"]
        )
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--trial-id", required=True)
    args = parser.parse_args()

    try:
        result = import_s1_events(args.source, args.trial_id)

        print("\nNARIS v1.0 TRIAL-AWARE S1 IMPORT")
        print("-" * 42)

        for key, value in result.items():
            print(f"{key}: {value}")

        print("Import completed.")

    except (GroundTruthError, FileNotFoundError, OSError) as error:
        print(f"IMPORT FAILED: {error}", file=sys.stderr)
        sys.exit(1)
