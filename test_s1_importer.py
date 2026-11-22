
import json
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from src.naris_gt import ground_truth
from src.naris_gt.scenarios import import_s1_events

from src.naris_gt.ground_truth import (
    GroundTruthRecorder,
    GroundTruthError
)


class TestS1Importer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.dataset_root = self.root / "final_dataset"
        self.dataset_root.mkdir()

        self.trial_id = "test-s1-trial-001"
        self.trial_dir = self.dataset_root / self.trial_id
        self.trial_dir.mkdir()

        self.level = "L1"

        self.metadata = {
            "experiment_id": self.trial_id,
            "dataset_role": "research_trial",
            "scenario_id": "S1",
            "status": "planned"
        }

        self.config = {
            "experiment_id": self.trial_id,
            "design_version": "1.0",
            "scenario_id": "S1",
            "degradation_level_id": self.level
        }

        self.write_json(
            self.trial_dir / "metadata.json",
            self.metadata
        )

        self.write_json(
            self.trial_dir / "experiment_config.json",
            self.config
        )

        self.source_path = self.root / "s1_raw_events.json"

        self.dataset_patch = patch.object(
            ground_truth,
            "DATASET_ROOT",
            self.dataset_root.resolve()
        )

        self.importer_patch = patch.object(
            import_s1_events,
            "DATASET_ROOT",
            self.dataset_root.resolve()
        )

        self.dataset_patch.start()
        self.importer_patch.start()

        self.events = self.create_source_events()
        self.write_json(self.source_path, self.create_envelope())

    def tearDown(self):
        self.importer_patch.stop()
        self.dataset_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def write_json(path, data):
        with Path(path).open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def create_source_events(self):
        actions = [
            "create_test_file",
            "access_file",
            "read_file",
            "stage_file_transfer",
            "transfer_file"
        ]

        events = []

        for sequence, action in enumerate(actions, start=1):
            events.append({
                "event_id": f"source-event-{sequence}",
                "experiment_id": self.trial_id,
                "scenario_id": "S1",
                "degradation_level_id": self.level,
                "run_id": "test-run-001",
                "sequence": sequence,
                "timestamp": (
                    f"2026-11-13T00:00:0{sequence}+00:00"
                ),
                "action": action,
                "host": "NARIS-Windows",
                "process": {
                    "name": "powershell",
                    "pid": 1234
                },
                "resource": {
                    "type": "file",
                    "path": f"C:/NARIS-Lab/test-{sequence}.txt"
                },
                "outcome": "success",
                "details": {
                    "test_event": True
                }
            })

        return events

    def create_envelope(self):
        return {
            "trial_id": self.trial_id,
            "experiment_id": self.trial_id,
            "scenario_id": "S1",
            "degradation_level_id": self.level,
            "run_id": "test-run-001",
            "source_ip": "192.168.56.20",
            "event_count": len(self.events),
            "events": self.events
        }

    def save_events(self):
        self.write_json(
            self.source_path,
            self.create_envelope()
        )

    def test_successful_import(self):
        result = import_s1_events.import_s1_events(
            self.source_path,
            self.trial_id
        )

        self.assertEqual(result["imported_events"], 5)
        self.assertEqual(result["total_ground_truth_events"], 5)
        self.assertEqual(result["degradation_level_id"], self.level)
        self.assertTrue(result["hash_chain_valid"])

    def test_duplicate_import_is_rejected(self):
        import_s1_events.import_s1_events(
            self.source_path,
            self.trial_id
        )

        with self.assertRaises(GroundTruthError):
            import_s1_events.import_s1_events(
                self.source_path,
                self.trial_id
            )

    def test_all_degradation_levels_are_supported(self):
        for level in ["L0", "L1", "L2", "L3", "L4"]:
            with self.subTest(level=level):
                trial_id = f"test-s1-{level}"
                trial_dir = self.dataset_root / trial_id
                trial_dir.mkdir()

                self.write_json(
                    trial_dir / "metadata.json",
                    {
                        "experiment_id": trial_id,
                        "dataset_role": "research_trial",
                        "scenario_id": "S1",
                        "status": "planned"
                    }
                )

                self.write_json(
                    trial_dir / "experiment_config.json",
                    {
                        "experiment_id": trial_id,
                        "design_version": "1.0",
                        "scenario_id": "S1",
                        "degradation_level_id": level
                    }
                )

                original_trial = self.trial_id
                original_level = self.level
                original_events = self.events

                self.trial_id = trial_id
                self.level = level
                self.events = self.create_source_events()

                self.save_events()

                result = import_s1_events.import_s1_events(
                    self.source_path,
                    trial_id
                )

                self.assertEqual(
                    result["degradation_level_id"],
                    level
                )
                self.assertEqual(result["imported_events"], 5)

                self.trial_id = original_trial
                self.level = original_level
                self.events = original_events

    def test_wrong_scenario_is_rejected(self):
        self.events[0]["scenario_id"] = "S2"
        self.save_events()

        with self.assertRaises(GroundTruthError):
            import_s1_events.import_s1_events(
                self.source_path,
                self.trial_id
            )

    def test_invalid_action_sequence_is_rejected(self):
        self.events[1]["action"] = "unexpected_action"
        self.save_events()

        with self.assertRaises(GroundTruthError):
            import_s1_events.import_s1_events(
                self.source_path,
                self.trial_id
            )

    def test_failed_execution_is_not_imported(self):
        self.events[2]["outcome"] = "failure"
        self.save_events()

        with self.assertRaises(GroundTruthError):
            import_s1_events.import_s1_events(
                self.source_path,
                self.trial_id
            )

        recorder = GroundTruthRecorder(self.trial_dir)

        self.assertEqual(recorder.get_event_count(), 0)

    def test_source_level_mismatch_is_rejected(self):
        self.events[0]["degradation_level_id"] = "L2"
        self.save_events()

        with self.assertRaises(GroundTruthError):
            import_s1_events.import_s1_events(
                self.source_path,
                self.trial_id
            )

    def test_wrong_source_ip_is_rejected(self):
        envelope = self.create_envelope()
        envelope["source_ip"] = "192.168.57.20"
        self.write_json(self.source_path, envelope)

        with self.assertRaises(GroundTruthError):
            import_s1_events.import_s1_events(
                self.source_path,
                self.trial_id
            )


if __name__ == "__main__":
    unittest.main()
