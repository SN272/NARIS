
import uuid

from datetime import datetime, timezone


ALLOWED_OUTCOMES = {
    "success",
    "failed",
    "not_executed"
}

REQUIRED_EVENT_FIELDS = {
    "experiment_id",
    "event_id",
    "sequence",
    "event_type",
    "action",
    "target",
    "outcome",
    "timestamp",
    "details",
    "evidence_reference"
}


def utc_now():
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def create_event(
    experiment_id,
    sequence,
    event_type,
    action,
    target,
    outcome,
    details=None,
    evidence_reference=None,
    timestamp=None
):
    """
    Create one event record from supplied execution information.

    This function does not execute an incident, generate sample events,
    create experiment directories, or save data.
    """
    event = {
        "experiment_id": experiment_id,
        "event_id": str(uuid.uuid4()),
        "sequence": sequence,
        "event_type": event_type,
        "action": action,
        "target": target,
        "outcome": outcome,
        "timestamp": timestamp or utc_now(),
        "details": details if details is not None else {},
        "evidence_reference": evidence_reference
    }

    valid, message = validate_event(event)

    if not valid:
        raise ValueError(message)

    return event


def validate_event(event):
    """Validate the structure and basic consistency of an event."""
    if not isinstance(event, dict):
        return False, "Event must be a dictionary"

    missing_fields = REQUIRED_EVENT_FIELDS - set(event.keys())

    if missing_fields:
        return False, f"Missing fields: {', '.join(sorted(missing_fields))}"

    if not isinstance(event["experiment_id"], str) or not event["experiment_id"].strip():
        return False, "Invalid experiment ID"

    if not isinstance(event["sequence"], int) or isinstance(event["sequence"], bool):
        return False, "Sequence must be an integer"

    if event["sequence"] < 1:
        return False, "Sequence number must be at least 1"

    if not isinstance(event["event_type"], str) or not event["event_type"].strip():
        return False, "Event type cannot be empty"

    if not isinstance(event["action"], str) or not event["action"].strip():
        return False, "Action cannot be empty"

    if not isinstance(event["target"], str) or not event["target"].strip():
        return False, "Target cannot be empty"

    if event["outcome"] not in ALLOWED_OUTCOMES:
        return False, "Invalid execution outcome"

    if not isinstance(event["timestamp"], str) or not event["timestamp"].strip():
        return False, "Timestamp is missing"

    try:
        datetime.fromisoformat(
            event["timestamp"].replace("Z", "+00:00")
        )
    except ValueError:
        return False, "Timestamp must be valid ISO 8601"

    if not isinstance(event["details"], dict):
        return False, "Event details must be a dictionary"

    evidence_reference = event["evidence_reference"]

    if evidence_reference is not None:
        if not isinstance(evidence_reference, str) or not evidence_reference.strip():
            return False, "Evidence reference must be a non-empty string or null"

    return True, "Event is valid"


def validate_event_sequence(events, experiment_id=None):
    """
    Validate an ordered collection of events.

    Checks sequence continuity, event structure, and experiment ID
    consistency. Does not access ground truth or evidence files.
    """
    if not isinstance(events, list):
        return False, ["Events must be a list"]

    errors = []

    for expected_sequence, event in enumerate(events, start=1):
        valid, message = validate_event(event)

        if not valid:
            errors.append(
                f"Event at position {expected_sequence}: {message}"
            )
            continue

        if event["sequence"] != expected_sequence:
            errors.append(
                f"Expected sequence {expected_sequence}, "
                f"found {event['sequence']}"
            )

        if experiment_id is not None:
            if event["experiment_id"] != experiment_id:
                errors.append(
                    f"Event {expected_sequence} has a mismatched experiment ID"
                )

    if errors:
        return False, errors

    return True, ["All events are valid"]
