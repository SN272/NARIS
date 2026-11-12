
import copy
import tempfile
import unittest
from pathlib import Path

from src.naris_gt.integrity import (
    register_manifest,
    verify_manifest_anchor
)


class TestManifestIntegrity(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = str(
            Path(self.temp_dir.name) / "integrity_registry.json"
        )

        self.experiment_id = "test-experiment-001"

        self.original_manifest = {
            "final_hash": "a" * 64
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registered_manifest_is_verified(self):
        register_manifest(
            self.experiment_id,
            self.original_manifest,
            self.registry_path
        )

        is_valid, message = verify_manifest_anchor(
            self.experiment_id,
            self.original_manifest,
            self.registry_path
        )

        self.assertTrue(is_valid, message)

    def test_tampered_manifest_replacement_is_rejected(self):
        register_manifest(
            self.experiment_id,
            self.original_manifest,
            self.registry_path
        )

        modified_manifest = copy.deepcopy(
            self.original_manifest
        )

        modified_manifest["final_hash"] = "0" * 64

        with self.assertRaises(ValueError):
            register_manifest(
                self.experiment_id,
                modified_manifest,
                self.registry_path
            )

    def test_original_manifest_remains_trusted_after_replacement_attempt(self):
        register_manifest(
            self.experiment_id,
            self.original_manifest,
            self.registry_path
        )

        modified_manifest = copy.deepcopy(
            self.original_manifest
        )

        modified_manifest["final_hash"] = "0" * 64

        try:
            register_manifest(
                self.experiment_id,
                modified_manifest,
                self.registry_path
            )
        except ValueError:
            pass

        is_valid, message = verify_manifest_anchor(
            self.experiment_id,
            self.original_manifest,
            self.registry_path
        )

        self.assertTrue(is_valid, message)


if __name__ == "__main__":
    unittest.main()
