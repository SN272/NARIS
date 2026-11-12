
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = PROJECT_ROOT / "config" / "experiment_matrix.json"


class ExperimentMatrixError(ValueError):
    """Raised when the experiment matrix is invalid."""


def load_experiment_matrix(path=MATRIX_PATH):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Experiment matrix not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        matrix = json.load(file)

    validate_experiment_matrix(matrix)
    return matrix


def validate_experiment_matrix(matrix):
    required_fields = [
        "project",
        "dataset_role",
        "scenarios",
        "degradation_levels",
        "trials_per_combination",
        "reconstruction_modes",
        "expected_trials",
        "expected_reconstruction_runs",
        "ground_truth_policy",
        "execution"
    ]

    missing = [
        field for field in required_fields
        if field not in matrix
    ]

    if missing:
        raise ExperimentMatrixError(
            f"Missing matrix fields: {', '.join(missing)}"
        )

    if matrix["project"] != "NARIS":
        raise ExperimentMatrixError(
            "Project identifier must be NARIS."
        )

    if matrix["dataset_role"] != "research_trial":
        raise ExperimentMatrixError(
            "Dataset role must be research_trial."
        )

    scenarios = matrix["scenarios"]
    levels = matrix["degradation_levels"]
    modes = matrix["reconstruction_modes"]
    repetitions = matrix["trials_per_combination"]

    if not isinstance(scenarios, list) or not scenarios:
        raise ExperimentMatrixError(
            "At least one scenario is required."
        )

    if not isinstance(levels, list) or not levels:
        raise ExperimentMatrixError(
            "At least one degradation level is required."
        )

    if not isinstance(modes, list) or not modes:
        raise ExperimentMatrixError(
            "At least one reconstruction mode is required."
        )

    if not isinstance(repetitions, int) or repetitions < 1:
        raise ExperimentMatrixError(
            "trials_per_combination must be a positive integer."
        )

    scenario_ids = [item.get("id") for item in scenarios]
    level_ids = [item.get("id") for item in levels]

    if len(scenario_ids) != len(set(scenario_ids)):
        raise ExperimentMatrixError(
            "Duplicate scenario IDs detected."
        )

    if len(level_ids) != len(set(level_ids)):
        raise ExperimentMatrixError(
            "Duplicate degradation level IDs detected."
        )

    expected_trials = (
        len(scenarios) * len(levels) * repetitions
    )

    expected_runs = expected_trials * len(modes)

    if matrix["expected_trials"] != expected_trials:
        raise ExperimentMatrixError(
            f"Expected trials mismatch: configured "
            f"{matrix['expected_trials']}, calculated "
            f"{expected_trials}."
        )

    if matrix["expected_reconstruction_runs"] != expected_runs:
        raise ExperimentMatrixError(
            f"Expected reconstruction runs mismatch: configured "
            f"{matrix['expected_reconstruction_runs']}, calculated "
            f"{expected_runs}."
        )

    policy = matrix["ground_truth_policy"]

    if policy.get("separate_storage") is not True:
        raise ExperimentMatrixError(
            "Ground truth must use separate storage."
        )

    if policy.get("accessible_to_reconstruction") is not False:
        raise ExperimentMatrixError(
            "Reconstruction engines must not access ground truth."
        )

    if policy.get("evaluation_only") is not True:
        raise ExperimentMatrixError(
            "Ground truth must be reserved for evaluation."
        )

    return True


def get_experiment_summary(matrix=None):
    if matrix is None:
        matrix = load_experiment_matrix()

    scenario_count = len(matrix["scenarios"])
    level_count = len(matrix["degradation_levels"])
    repetitions = matrix["trials_per_combination"]
    mode_count = len(matrix["reconstruction_modes"])

    total_trials = (
        scenario_count * level_count * repetitions
    )

    total_runs = total_trials * mode_count

    return {
        "scenario_count": scenario_count,
        "degradation_level_count": level_count,
        "trials_per_combination": repetitions,
        "reconstruction_mode_count": mode_count,
        "total_trials": total_trials,
        "total_reconstruction_runs": total_runs
    }


if __name__ == "__main__":
    matrix = load_experiment_matrix()
    summary = get_experiment_summary(matrix)

    print("NARIS EXPERIMENT MATRIX")
    print("-" * 40)

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("-" * 40)
    print("Matrix validation: PASSED")
