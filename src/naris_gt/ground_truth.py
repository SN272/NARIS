
import hashlib
import json
import uuid

from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_ROOT = (
    PROJECT_ROOT
    / "experiment_data"
    / "naris_v1"
    / "final_dataset"
).resolve()

SCHEMA_VERSION = "1.0"
GENESIS_HASH = "0" * 64

ALLOWED_OUTCOMES = {
    "success",
    "failure",
    "partial"
}


class GroundTruthError(Exception):
    """Raised when ground-truth recording or validation fails."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )


def calculate_event_hash(event):
    event_content = {
        key: value
        for key, value in event.items()
        if key != "event_hash"
    }

    return hashlib.sha256(
        canonical_json(event_content).encode("utf-8")
    ).hexdigest()


def validate_timestamp(timestamp):
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise GroundTruthError("A valid UTC timestamp is required.")

    try:
        parsed = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise GroundTruthError(
            "Timestamp must be a valid ISO 8601 value."
        ) from error

    if parsed.tzinfo is None:
        raise GroundTruthError(
            "Timestamp must include a timezone."
        )

    if parsed.utcoffset().total_seconds() != 0:
        raise GroundTruthError(
            "Ground-truth timestamps must use UTC."
        )

    return timestamp


class GroundTruthRecorder:

    def __init__(self, trial_directory):
        self.trial_directory = Path(trial_directory).resolve()

        self._validate_trial_directory()

        self.metadata_path = self.trial_directory / "metadata.json"
        self.config_path = self.trial_directory / "experiment_config.json"

        self.metadata = self._read_json(self.metadata_path)
        self.config = self._read_json(self.config_path)

        self.experiment_id = self.metadata.get("experiment_id")
        self.scenario_id = self.metadata.get("scenario_id")

        if self.metadata.get("dataset_role") != "research_trial":
            raise GroundTruthError(
                "Only research_trial directories can store ground truth."
            )

        if not self.experiment_id or not self.scenario_id:
            raise GroundTruthError(
                "Trial metadata must contain experiment_id and scenario_id."
            )

        if self.trial_directory.name != self.experiment_id:
            raise GroundTruthError(
                "Trial directory name does not match experiment_id."
            )

        if self.config.get("experiment_id") != self.experiment_id:
            raise GroundTruthError(
                "Trial metadata and configuration IDs do not match."
            )

        if self.config.get("scenario_id") != self.scenario_id:
            raise GroundTruthError(
                "Trial metadata and configuration scenarios do not match."
            )

        self.ground_truth_directory = (
            self.trial_directory / "ground_truth"
        )

        self.ground_truth_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.events_path = (
            self.ground_truth_directory / "events.json"
        )

        self._validate_storage_path()

    def _validate_trial_directory(self):
        if not self.trial_directory.is_dir():
            raise GroundTruthError(
                f"Trial directory does not exist: {self.trial_directory}"
            )

        try:
            relative_path = self.trial_directory.relative_to(
                DATASET_ROOT
            )
        except ValueError as error:
            raise GroundTruthError(
                "Ground truth can only be recorded inside "
                "experiment_data/naris_v1/final_dataset."
            ) from error

        if len(relative_path.parts) != 1:
            raise GroundTruthError(
                "A trial directory must be a direct child "
                "of the NARIS v1.0 final dataset directory."
            )

    def _validate_storage_path(self):
        resolved_path = self.ground_truth_directory.resolve()

        try:
            resolved_path.relative_to(self.trial_directory)
        except ValueError as error:
            raise GroundTruthError(
                "Ground-truth storage must remain inside its trial."
            ) from error

    @staticmethod
    def _read_json(path):
        if not path.is_file():
            raise GroundTruthError(
                f"Required trial file is missing: {path.name}"
            )

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError) as error:
            raise GroundTruthError(
                f"Could not read {path.name}: {error}"
            ) from error

    def _load_event_store(self):
        if not self.events_path.exists():
            return {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": self.experiment_id,
                "scenario_id": self.scenario_id,
                "event_count": 0,
                "events": []
            }

        store = self._read_json(self.events_path)

        if store.get("experiment_id") != self.experiment_id:
            raise GroundTruthError(
                "Ground-truth file belongs to another experiment."
            )

        if store.get("scenario_id") != self.scenario_id:
            raise GroundTruthError(
                "Ground-truth scenario does not match trial metadata."
            )

        if not isinstance(store.get("events"), list):
            raise GroundTruthError(
                "Ground-truth events must be stored as a list."
            )

        if store.get("event_count") != len(store["events"]):
            raise GroundTruthError(
                "Ground-truth event count does not match stored events."
            )

        if not self.verify_event_chain(store["events"]):
            raise GroundTruthError(
                "Ground-truth event chain verification failed."
            )

        return store

    @staticmethod
    def verify_event_chain(events):
        previous_hash = GENESIS_HASH

        for expected_sequence, event in enumerate(events, start=1):
            if event.get("sequence") != expected_sequence:
                return False

            if event.get("previous_event_hash") != previous_hash:
                return False

            calculated_hash = calculate_event_hash(event)

            if event.get("event_hash") != calculated_hash:
                return False

            previous_hash = calculated_hash

        return True

    def record_event(
        self,
        action,
        host,
        outcome="success",
        process=None,
        resource=None,
        details=None,
        timestamp=None
    ):
        if not isinstance(action, str) or not action.strip():
            raise GroundTruthError("Event action is required.")

        if not isinstance(host, str) or not host.strip():
            raise GroundTruthError("Event host is required.")

        if outcome not in ALLOWED_OUTCOMES:
            raise GroundTruthError(
                f"Outcome must be one of: {', '.join(sorted(ALLOWED_OUTCOMES))}"
            )

        if process is not None and not isinstance(process, dict):
            raise GroundTruthError("Process information must be a dictionary.")

        if resource is not None and not isinstance(resource, dict):
            raise GroundTruthError("Resource information must be a dictionary.")

        if details is not None and not isinstance(details, dict):
            raise GroundTruthError("Event details must be a dictionary.")

        timestamp = validate_timestamp(timestamp or utc_now())

        store = self._load_event_store()
        events = store["events"]

        previous_hash = (
            events[-1]["event_hash"]
            if events
            else GENESIS_HASH
        )

        event = {
            "event_id": str(uuid.uuid4()),
            "experiment_id": self.experiment_id,
            "scenario_id": self.scenario_id,
            "sequence": len(events) + 1,
            "timestamp": timestamp,
            "action": action.strip(),
            "host": host.strip(),
            "process": process or {},
            "resource": resource or {},
            "outcome": outcome,
            "details": details or {},
            "previous_event_hash": previous_hash
        }

        event["event_hash"] = calculate_event_hash(event)

        events.append(event)

        store["event_count"] = len(events)
        store["events"] = events

        self._write_event_store(store)

        return event

    def _write_event_store(self, store):
        temporary_path = self.events_path.with_suffix(".json.tmp")

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    store,
                    file,
                    indent=4,
                    ensure_ascii=False
                )
                file.write("\n")

            temporary_path.replace(self.events_path)

        except OSError as error:
            if temporary_path.exists():
                temporary_path.unlink()

            raise GroundTruthError(
                f"Could not save ground-truth events: {error}"
            ) from error

    def get_event_count(self):
        return self._load_event_store()["event_count"]


if __name__ == "__main__":
    print("NARIS Ground-Truth Recorder")
    print("-" * 40)
    print("Module loaded successfully.")
    print("No experimental events were generated.")
    print("Ground-truth storage is restricted to NARIS v1.0 research trials.")
