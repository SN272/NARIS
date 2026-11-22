
import json
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from src.naris_gt import ground_truth
from src.naris_gt.ground_truth import (
    GroundTruthError,
    GroundTruthRecorder
)


class TestGroundTruthRecorder(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dataset_root = Path(self.temp_dir.name) / "final_dataset"
        self.dataset_root.mkdir()

        self.dataset_patch = patch.object(
            ground_truth,
            "DATASET_ROOT",
            self.dataset_root.resolve()
        )
        self.dataset_patch.start()

        self.experiment_id = "test-trial-001"
        self.trial_dir = self.dataset_root / self.experiment_id
        self.trial_dir.mkdir()

        self.metadata = {
            "experiment_id": self.experiment_id,
            "dataset_role": "research_trial",
            "scenario_id": "S1",
            "status": "planned"
        }

        self.config = {
            "experiment_id": self.experiment_id,
            "scenario_id": "S1"
        }

        self.write_trial_files()

        self.recorder = GroundTruthRecorder(self.trial_dir)

    def tearDown(self):
        self.dataset_patch.stop()
        self.temp_dir.cleanup()

    def write_trial_files(self):
        with (self.trial_dir / "metadata.json").open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(self.metadata, file)

        with (self.trial_dir / "experiment_config.json").open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(self.config, file)

    def test_records_event_with_valid_hash(self):
        event = self.recorder.record_event(
            action="file_access",
            host="NARIS-Windows",
            resource={"path": "C:/NARIS-Lab/sample.txt"}
        )

        self.assertEqual(event["sequence"], 1)
        self.assertTrue(
            GroundTruthRecorder.verify_event_chain([event])
        )

    def test_event_sequence_and_hash_chain(self):
        first = self.recorder.record_event(
            action="file_access",
            host="NARIS-Windows"
        )

        second = self.recorder.record_event(
            action="file_transfer",
            host="NARIS-Windows"
        )

        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(
            second["previous_event_hash"],
            first["event_hash"]
        )

        self.assertEqual(self.recorder.get_event_count(), 2)

    def test_modified_event_is_detected(self):
        self.recorder.record_event(
            action="file_access",
            host="NARIS-Windows"
        )

        with self.recorder.events_path.open(
            "r", encoding="utf-8"
        ) as file:
            store = json.load(file)

        store["events"][0]["action"] = "modified_action"

        with self.recorder.events_path.open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(store, file)

        with self.assertRaises(GroundTruthError):
            self.recorder.get_event_count()

    def test_pilot_directory_is_rejected(self):
        self.metadata["dataset_role"] = "pilot"
        self.write_trial_files()

        with self.assertRaises(GroundTruthError):
            GroundTruthRecorder(self.trial_dir)

    def test_non_utc_timestamp_is_rejected(self):
        with self.assertRaises(GroundTruthError):
            self.recorder.record_event(
                action="file_access",
                host="NARIS-Windows",
                timestamp="2026-11-13T10:00:00"
            )

    def test_invalid_outcome_is_rejected(self):
        with self.assertRaises(GroundTruthError):
            self.recorder.record_event(
                action="file_access",
                host="NARIS-Windows",
                outcome="unknown"
            )


if __name__ == "__main__":
    unittest.main()
