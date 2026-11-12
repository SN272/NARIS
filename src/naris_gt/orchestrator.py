
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.naris_gt.experiment_matrix import load_experiment_matrix


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "experiment_data" / "final_dataset"
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
        "evidence/host",
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
        "repetition": trial["repetition"],
        "reconstruction_modes": matrix["reconstruction_modes"],
        "random_seed": matrix["execution"]["random_seed"],
        "ground_truth_location": "ground_truth",
        "ground_truth_access": "evaluation_only"
    }

    write_json(trial_dir / "metadata.json", metadata)
    write_json(trial_dir / "experiment_config.json", experiment_config)

    return trial_dir


def initialise_batch():
    matrix = load_experiment_matrix()

    DATASET_ROOT.mkdir(parents=True, exist_ok=True)

    if BATCH_MANIFEST.exists():
        raise FileExistsError(
            "A batch manifest already exists. "
            "The orchestrator will not overwrite an existing batch."
        )

    existing_trials = [
        path for path in DATASET_ROOT.iterdir()
        if path.is_dir()
    ]

    if existing_trials:
        raise FileExistsError(
            "The final dataset directory already contains trial folders. "
            "Use a new empty dataset directory or review the existing batch."
        )

    plan = build_trial_plan(matrix)

    batch = {
        "batch_id": str(uuid.uuid4()),
        "project": "NARIS",
        "dataset_role": "research_trial",
        "design_version": matrix["design_version"],
        "created_at": utc_now(),
        "status": "initialising",
        "planned_trials": len(plan),
        "created_trials": 0,
        "failed_trials": 0,
        "trials": []
    }

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

        # Persist progress after each trial so failures are not lost.
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

    print("\nNARIS BATCH INITIALISATION")
    print("-" * 42)
    print(f"Batch ID: {result['batch_id']}")
    print(f"Planned trials: {result['planned_trials']}")
    print(f"Created workspaces: {result['created_trials']}")
    print(f"Failed initialisations: {result['failed_trials']}")
    print(f"Final status: {result['status']}")
    print(f"Dataset directory: {DATASET_ROOT}")
    print("-" * 42)
