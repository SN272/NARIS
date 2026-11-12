
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FINAL_DATASET_ROOT = PROJECT_ROOT / "experiment_data" / "final_dataset"


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_experiment_directory(experiment_id):
    """
    Find an experiment by its metadata ID, searching only the
    final research dataset.
    """
    if not FINAL_DATASET_ROOT.exists():
        raise FileNotFoundError(
            f"Final dataset directory not found: {FINAL_DATASET_ROOT}"
        )

    for metadata_path in FINAL_DATASET_ROOT.rglob("metadata.json"):
        try:
            metadata = read_json(metadata_path)
        except (OSError, json.JSONDecodeError):
            continue

        if (
            metadata.get("experiment_id") == experiment_id
            and metadata.get("dataset_role") == "research_trial"
        ):
            return metadata_path.parent

    raise FileNotFoundError(
        f"Research experiment not found: {experiment_id}"
    )


def load_experiment(experiment_id):
    experiment_directory = find_experiment_directory(experiment_id)

    metadata_path = experiment_directory / "metadata.json"
    config_path = experiment_directory / "experiment_config.json"

    metadata = read_json(metadata_path)

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Experiment configuration missing: {experiment_id}"
        )

    config = read_json(config_path)

    events_path = experiment_directory / "events.json"
    ground_truth_path = experiment_directory / "ground_truth.json"
    collection_events_path = (
        experiment_directory / "collection_events.json"
    )

    events = (
        read_json(events_path)
        if events_path.is_file()
        else []
    )

    ground_truth = (
        read_json(ground_truth_path)
        if ground_truth_path.is_file()
        else []
    )

    collection_events = (
        read_json(collection_events_path)
        if collection_events_path.is_file()
        else []
    )

    return {
        "experiment_id": experiment_id,
        "directory": experiment_directory,
        "metadata": metadata,
        "config": config,
        "events": events,
        "ground_truth": ground_truth,
        "collection_events": collection_events
    }


def list_experiments():
    """
    List only completed research trials.
    Pilot and incomplete experiments are excluded.
    """
    if not FINAL_DATASET_ROOT.exists():
        return []

    experiment_ids = []

    for metadata_path in FINAL_DATASET_ROOT.rglob("metadata.json"):
        try:
            metadata = read_json(metadata_path)
        except (OSError, json.JSONDecodeError):
            continue

        if (
            metadata.get("dataset_role") == "research_trial"
            and metadata.get("status") == "completed"
            and metadata.get("experiment_id")
        ):
            experiment_ids.append(metadata["experiment_id"])

    return sorted(set(experiment_ids))


def load_all_experiments():
    all_experiments = []

    for experiment_id in list_experiments():
        try:
            all_experiments.append(load_experiment(experiment_id))

        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(
                f"Could not load research experiment "
                f"{experiment_id}: {error}"
            )

    return all_experiments


def validate_experiment_records(experiment):
    errors = []

    metadata = experiment["metadata"]
    config = experiment["config"]
    experiment_id = metadata.get("experiment_id")

    if metadata.get("dataset_role") != "research_trial":
        errors.append("Experiment is not marked as a research trial")

    if metadata.get("status") != "completed":
        errors.append("Research experiment is not completed")

    if not experiment_id:
        errors.append("Experiment ID is missing")

    if config.get("experiment_id") != experiment_id:
        errors.append(
            "Configuration experiment ID does not match metadata"
        )

    if metadata.get("scenario") != config.get("scenario"):
        errors.append(
            "Metadata scenario does not match configuration"
        )

    events = experiment.get("events", [])

    if events:
        sequences = [
            event.get("sequence") for event in events
        ]

        expected_sequences = list(range(1, len(events) + 1))

        if sequences != expected_sequences:
            errors.append(
                "Event sequence is missing, duplicated, or out of order"
            )

        for event in events:
            if event.get("experiment_id") != experiment_id:
                errors.append(
                    "Event experiment ID does not match metadata"
                )
                break

    return len(errors) == 0, errors
