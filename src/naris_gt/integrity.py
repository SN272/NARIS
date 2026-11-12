
import os
import json
import hashlib
from pathlib import Path


GENESIS_HASH = "0" * 64


def canonicalize_event(event):
    canonical_data = json.dumps(
        event,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )

    return canonical_data.encode("utf-8")


def calculate_event_hash(event):
    canonical_data = canonicalize_event(event)
    return hashlib.sha256(canonical_data).hexdigest()


def generate_hash_chain(events):
    hash_chain = []
    previous_hash = GENESIS_HASH

    for event in events:
        canonical_data = canonicalize_event(event)
        chain_data = canonical_data + previous_hash.encode("utf-8")
        current_hash = hashlib.sha256(chain_data).hexdigest()

        hash_chain.append({
            "event_id": event["event_id"],
            "sequence": event["sequence"],
            "previous_hash": previous_hash,
            "event_hash": current_hash
        })

        previous_hash = current_hash

    return hash_chain


def create_integrity_manifest(experiment_id, events):
    hash_chain = generate_hash_chain(events)

    manifest = {
        "experiment_id": experiment_id,
        "hash_algorithm": "SHA-256",
        "genesis_hash": GENESIS_HASH,
        "total_events": len(events),
        "hash_chain": hash_chain,
        "final_hash": (
            hash_chain[-1]["event_hash"]
            if hash_chain
            else GENESIS_HASH
        )
    }

    return manifest


def calculate_manifest_hash(manifest):
    canonical_manifest = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    return hashlib.sha256(canonical_manifest).hexdigest()


def register_manifest(experiment_id, manifest, registry_path):
    manifest_hash = calculate_manifest_hash(manifest)

    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as file:
            registry = json.load(file)
    else:
        registry = {
            "hash_algorithm": "SHA-256",
            "experiments": {}
        }

    existing_hash = registry["experiments"].get(experiment_id)

    if existing_hash is not None:
        if existing_hash == manifest_hash:
            return manifest_hash

        raise ValueError(
            "Experiment already has a different registered manifest hash"
        )

    registry["experiments"][experiment_id] = manifest_hash

    with open(registry_path, "w", encoding="utf-8") as file:
        json.dump(registry, file, indent=4)

    return manifest_hash


def verify_integrity(events, manifest):
    errors = []

    if len(events) != manifest["total_events"]:
        errors.append("Event count mismatch")

    if len(events) != len(manifest["hash_chain"]):
        errors.append("Hash-chain length mismatch")

    if errors:
        return False, errors

    calculated_chain = generate_hash_chain(events)

    for index, calculated_record in enumerate(calculated_chain):
        stored_record = manifest["hash_chain"][index]

        if calculated_record != stored_record:
            errors.append(
                f"Integrity verification failed at event {index + 1}"
            )

    calculated_final_hash = (
        calculated_chain[-1]["event_hash"]
        if calculated_chain
        else GENESIS_HASH
    )

    if calculated_final_hash != manifest["final_hash"]:
        errors.append("Final hash mismatch")

    if errors:
        return False, errors

    return True, ["Integrity verification successful"]


def verify_manifest_anchor(experiment_id, manifest, registry_path):
    if not os.path.isfile(registry_path):
        return False, "Integrity registry not found"

    with open(registry_path, "r", encoding="utf-8") as file:
        registry = json.load(file)

    registered_hash = registry.get(
        "experiments", {}
    ).get(experiment_id)

    if registered_hash is None:
        return False, "Experiment not registered"

    calculated_hash = calculate_manifest_hash(manifest)

    if calculated_hash != registered_hash:
        return False, "Manifest hash mismatch"

    return True, "Manifest anchor verification successful"


def verify_evidence_files(events, experiment_dir):
    """
    Verify collected JSON evidence files against the SHA-256 values
    recorded in each event's details.record_sha256 field.

    The evidence hash uses the same canonical JSON serialization
    as the NARIS controller.
    """
    experiment_dir = Path(experiment_dir).resolve()
    errors = []
    verified = 0

    for event in events:
        evidence_reference = event.get("evidence_reference")
        details = event.get("details", {})
        expected_hash = details.get("record_sha256")

        if not evidence_reference:
            errors.append(
                f"Event {event.get('event_id', 'unknown')}: "
                "missing evidence_reference"
            )
            continue

        if not expected_hash:
            errors.append(
                f"Event {event.get('event_id', 'unknown')}: "
                "missing details.record_sha256"
            )
            continue

        evidence_path = (
            experiment_dir / evidence_reference
        ).resolve()

        # Prevent references from escaping the experiment directory.
        if not evidence_path.is_relative_to(experiment_dir):
            errors.append(
                f"Event {event.get('event_id', 'unknown')}: "
                "invalid evidence path"
            )
            continue

        if not evidence_path.is_file():
            errors.append(
                f"Event {event.get('event_id', 'unknown')}: "
                f"evidence file not found: {evidence_reference}"
            )
            continue

        try:
            with evidence_path.open("r", encoding="utf-8") as file:
                record = json.load(file)

            canonical_record = json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False
            ).encode("utf-8")

            actual_hash = hashlib.sha256(
                canonical_record
            ).hexdigest()

        except (OSError, json.JSONDecodeError, TypeError) as error:
            errors.append(
                f"Event {event.get('event_id', 'unknown')}: "
                f"could not verify evidence file: {error}"
            )
            continue

        if actual_hash != expected_hash:
            errors.append(
                f"Event {event.get('event_id', 'unknown')}: "
                f"evidence hash mismatch for {evidence_reference}"
            )
        else:
            verified += 1

    if errors:
        return False, {
            "verified_files": verified,
            "errors": errors
        }

    return True, {
        "verified_files": verified,
        "message": "All evidence files verified successfully"
    }
