
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.naris_gt.experiment_matrix import load_experiment_matrix


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_ROOT = (
    PROJECT_ROOT
    / "experiment_data"
    / "naris_v1"
    / "final_dataset"
)

BATCH_MANIFEST = DATASET_ROOT / "batch_manifest.json"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
        file.write("\n")

    temporary_path.replace(path)


def validate_v1_matrix(matrix):
    if matrix.get("design_version") != "1.0":
        raise ValueError("Only NARIS v1.0 is supported.")

    scenarios = matrix["scenarios"]
    levels = matrix["degradation_levels"]
    modes = matrix["reconstruction_modes"]

    if len(scenarios) != 1 or scenarios[0].get("id") != "S1":
        raise ValueError("v1.0 must contain exactly scenario S1.")

    expected_levels = ["L0", "L1", "L2", "L3", "L4"]
    actual_levels = [level.get("id") for level in levels]

    if actual_levels != expected_levels:
        raise ValueError(
            f"Expected degradation levels {expected_levels}, "
            f"received {actual_levels}."
        )

    if matrix["trials_per_combination"] != 10:
        raise ValueError("v1.0 requires exactly 10 repetitions per level.")

    expected_modes = ["host_only", "network_only", "combined"]

    if modes != expected_modes:
        raise ValueError(
            f"Expected reconstruction modes {expected_modes}."
        )

    if matrix["expected_trials"] != 50:
        raise ValueError("v1.0 must contain exactly 50 trials.")

    if matrix["expected_reconstruction_runs"] != 150:
        raise ValueError("v1.0 must contain exactly 150 reconstruction runs.")

    return True


def build_trial_plan(matrix):
    plan = []

    for scenario in matrix["scenarios"]:
        for level in matrix["degradation_levels"]:
            for repetition in range(
                1, matrix["trials_per_combination"] + 1
            ):
                trial_id = str(uuid.uuid4())

                plan.append({
                    "trial_id": trial_id,
                    "scenario_id": scenario["id"],
                    "scenario_name": scenario["name"],
                    "degradation_level_id": level["id"],
                    "degradation_level_name": level["name"],
                    "repetition": repetition,
                    "status": "planned"
                })

    return plan


def create_trial_workspace(trial, matrix):
    trial_id = trial["trial_id"]
    trial_dir = DATASET_ROOT / trial_id

    if trial_dir.exists():
        raise FileExistsError(
            f"Trial directory already exists: {trial_id}"
        )

    trial_dir.mkdir(parents=True, exist_ok=False)

    directories = [
        "ground_truth",
        "evidence/host/original",
        "evidence/host/degraded",
        "evidence/network",
        "reconstruction/host_only",
        "reconstruction/network_only",
        "reconstruction/combined",
        "evaluation"
    ]

    for directory in directories:
        (trial_dir / directory).mkdir(parents=True, exist_ok=True)

    metadata = {
        "experiment_id": trial_id,
        "project": "NARIS",
        "dataset_role": "research_trial",
        "design_version": matrix["design_version"],
        "status": "planned",
        "created_at": utc_now(),
        "scenario_id": trial["scenario_id"],
        "scenario_name": trial["scenario_name"],
        "degradation_level_id": trial["degradation_level_id"],
        "degradation_level_name": trial["degradation_level_name"],
        "repetition": trial["repetition"]
    }

    experiment_config = {
        "experiment_id": trial_id,
        "design_version": matrix["design_version"],
        "scenario_id": trial["scenario_id"],
        "degradation_level_id": trial["degradation_level_id"],
        "degradation_level_name": trial["degradation_level_name"],
        "repetition": trial["repetition"],
        "reconstruction_modes": matrix["reconstruction_modes"],
        "random_seed": matrix["execution"]["random_seed"],
        "ground_truth_location": "ground_truth",
        "ground_truth_access": "evaluation_only",
        "evidence_policy": matrix["evidence_policy"]
    }

    write_json(trial_dir / "metadata.json", metadata)
    write_json(trial_dir / "experiment_config.json", experiment_config)

    return trial_dir


def initialise_batch():
    matrix = load_experiment_matrix()
    validate_v1_matrix(matrix)

    if DATASET_ROOT.exists():
        raise FileExistsError(
            f"v1.0 dataset directory already exists: {DATASET_ROOT}. "
            "The orchestrator will not overwrite existing data."
        )

    DATASET_ROOT.mkdir(parents=True, exist_ok=False)

    plan = build_trial_plan(matrix)

    if len(plan) != 50:
        raise RuntimeError(
            f"Expected 50 trials, generated {len(plan)}."
        )

    batch = {
        "batch_id": str(uuid.uuid4()),
        "project": "NARIS",
        "dataset_role": "research_trial",
        "design_version": "1.0",
        "version": "NARIS-v1.0",
        "scenario_scope": ["S1"],
        "created_at": utc_now(),
        "status": "initialising",
        "planned_trials": len(plan),
        "created_trials": 0,
        "failed_trials": 0,
        "expected_reconstruction_runs": 150,
        "reconstruction_modes": matrix["reconstruction_modes"],
        "trials": []
    }

    # Persist the initial manifest before creating workspaces.
    write_json(BATCH_MANIFEST, batch)

    for trial in plan:
        try:
            create_trial_workspace(trial, matrix)
            trial["status"] = "planned"
            batch["created_trials"] += 1

        except Exception as error:
            trial["status"] = "initialisation_failed"
            trial["error"] = str(error)
            batch["failed_trials"] += 1

        batch["trials"].append(trial)

        # Persist progress after every trial.
        batch["status"] = "initialising"
        write_json(BATCH_MANIFEST, batch)

    if batch["failed_trials"] == 0:
        batch["status"] = "prepared"
    else:
        batch["status"] = "prepared_with_failures"

    batch["completed_at"] = utc_now()
    write_json(BATCH_MANIFEST, batch)

    return batch


if __name__ == "__main__":
    result = initialise_batch()

    print("\nNARIS v1.0 BATCH INITIALISATION")
    print("-" * 45)
    print(f"Batch ID: {result['batch_id']}")
    print(f"Design version: {result['design_version']}")
    print(f"Scenario scope: {result['scenario_scope']}")
    print(f"Planned trials: {result['planned_trials']}")
    print(f"Created workspaces: {result['created_trials']}")
    print(f"Failed initialisations: {result['failed_trials']}")
    print(
        "Expected reconstruction runs: "
        f"{result['expected_reconstruction_runs']}"
    )
    print(f"Final status: {result['status']}")
    print(f"Dataset directory: {DATASET_ROOT}")
    print("-" * 45)
