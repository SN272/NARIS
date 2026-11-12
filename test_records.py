
import json
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from src.naris_gt import records


class TestResearchDatasetIsolation(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.dataset_root = Path(self.temp_directory.name)

        self.experiment_id = "research-trial-test-001"
        self.experiment_directory = (
            self.dataset_root / "S1" / "L0" / self.experiment_id
        )

        self.experiment_directory.mkdir(parents=True)

        self.metadata = {
            "experiment_id": self.experiment_id,
            "dataset_role": "research_trial",
            "scenario": "S1",
            "degradation_level": "L0",
            "status": "completed",
            "total_events": 1,
            "completed_at": "2026-11-13T10:00:00+00:00"
        }

        self.config = {
            "experiment_id": self.experiment_id,
            "dataset_role": "research_trial",
            "scenario": "S1",
            "degradation_level": "L0",
            "trial_number": 1
        }

        self.events = [
            {
                "experiment_id": self.experiment_id,
                "event_id": "event-test-001",
                "sequence": 1,
                "event_type": "test_event",
                "action": "test_action",
                "target": "test_target",
                "outcome": "success",
                "timestamp": "2026-11-13T10:00:00+00:00",
                "details": {},
                "evidence_reference": None
            }
        ]

        self.write_json(
            self.experiment_directory / "metadata.json",
            self.metadata
        )

        self.write_json(
            self.experiment_directory / "experiment_config.json",
            self.config
        )

        self.write_json(
            self.experiment_directory / "events.json",
            self.events
        )

        self.write_json(
            self.experiment_directory / "ground_truth.json",
            self.events
        )

        self.write_json(
            self.experiment_directory / "collection_events.json",
            []
        )

        self.dataset_patch = patch.object(
            records,
            "FINAL_DATASET_ROOT",
            self.dataset_root
        )

        self.dataset_patch.start()

    def tearDown(self):
        self.dataset_patch.stop()
        self.temp_directory.cleanup()

    @staticmethod
    def write_json(path, data):
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def test_lists_completed_research_trial(self):
        experiment_ids = records.list_experiments()

        self.assertEqual(
            experiment_ids,
            [self.experiment_id]
        )

    def test_loads_research_trial(self):
        experiment = records.load_experiment(self.experiment_id)

        self.assertEqual(
            experiment["experiment_id"],
            self.experiment_id
        )

        self.assertEqual(
            experiment["metadata"]["dataset_role"],
            "research_trial"
        )

        self.assertEqual(len(experiment["events"]), 1)

    def test_pilot_records_are_not_loaded(self):
        pilot_directory = (
            self.dataset_root / "pilot_data" / "real_baseline"
        )

        pilot_directory.mkdir(parents=True)

        self.write_json(
            pilot_directory / "metadata.json",
            {
                "experiment_id": "pilot-test-001",
                "dataset_role": "pilot",
                "status": "completed"
            }
        )

        self.assertNotIn(
            "pilot-test-001",
            records.list_experiments()
        )

        with self.assertRaises(FileNotFoundError):
            records.load_experiment("pilot-test-001")

    def test_incomplete_trials_are_excluded(self):
        incomplete_id = "research-trial-incomplete"

        incomplete_directory = (
            self.dataset_root / "S1" / "L0" / incomplete_id
        )

        incomplete_directory.mkdir(parents=True)

        self.write_json(
            incomplete_directory / "metadata.json",
            {
                "experiment_id": incomplete_id,
                "dataset_role": "research_trial",
                "status": "collecting"
            }
        )

        self.assertNotIn(
            incomplete_id,
            records.list_experiments()
        )

    def test_invalid_sequence_is_detected(self):
        experiment = records.load_experiment(self.experiment_id)

        experiment["events"][0]["sequence"] = 2

        valid, errors = records.validate_experiment_records(experiment)

        self.assertFalse(valid)
        self.assertTrue(errors)

    def test_configuration_id_mismatch_is_detected(self):
        experiment = records.load_experiment(self.experiment_id)

        experiment["config"]["experiment_id"] = "different-id"

        valid, errors = records.validate_experiment_records(experiment)

        self.assertFalse(valid)
        self.assertIn(
            "Configuration experiment ID does not match metadata",
            errors
        )

    def test_empty_final_dataset_returns_no_experiments(self):
        empty_root = self.dataset_root / "empty"
        empty_root.mkdir()

        with patch.object(
            records,
            "FINAL_DATASET_ROOT",
            empty_root
        ):
            self.assertEqual(records.list_experiments(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
