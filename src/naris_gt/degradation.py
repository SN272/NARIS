
import hashlib
import json
import shutil

from datetime import datetime, timedelta, timezone
from pathlib import Path


LEVELS = {
    "L0": [],
    "L1": ["remove_noncritical"],
    "L2": ["remove_noncritical", "shift_file_timestamps"],
    "L3": [
        "remove_noncritical",
        "shift_file_timestamps",
        "remove_log_records"
    ],
    "L4": [
        "remove_noncritical",
        "shift_file_timestamps",
        "remove_log_records",
        "alter_log_timestamps"
    ]
}

TIMESTAMP_OFFSET_SECONDS = 3600
CATALOG_NAME = "artifact_catalog.json"


class DegradationError(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_catalog(source_directory):
    catalog_path = source_directory / CATALOG_NAME

    if not catalog_path.is_file():
        raise DegradationError(
            f"Missing artifact catalog: {CATALOG_NAME}"
        )

    try:
        catalog = json.loads(
            catalog_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise DegradationError(
            f"Could not read artifact catalog: {error}"
        ) from error

    if not isinstance(catalog, dict):
        raise DegradationError("Catalog must be a JSON object.")

    artifacts = catalog.get("artifacts")

    if not isinstance(artifacts, list):
        raise DegradationError("Catalog artifacts must be a list.")

    seen = set()

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise DegradationError("Invalid artifact entry.")

        relative_path = artifact.get("path")

        if not isinstance(relative_path, str) or not relative_path:
            raise DegradationError("Artifact path is required.")

        path = Path(relative_path)

        if path.is_absolute() or ".." in path.parts:
            raise DegradationError(
                f"Unsafe artifact path: {relative_path}"
            )

        if relative_path in seen:
            raise DegradationError(
                f"Duplicate artifact path: {relative_path}"
            )

        seen.add(relative_path)

        if artifact.get("criticality") not in {
            "noncritical", "important", "critical"
        }:
            raise DegradationError(
                f"Invalid criticality for {relative_path}"
            )

        for field in (
            "timestamp_sensitive",
            "removable_record_ids",
            "alter_record_ids"
        ):
            if field not in artifact:
                continue

            value = artifact[field]

            if field == "timestamp_sensitive":
                if not isinstance(value, bool):
                    raise DegradationError(
                        f"{field} must be boolean: {relative_path}"
                    )
            elif (
                not isinstance(value, list)
                or not all(isinstance(item, str) for item in value)
            ):
                raise DegradationError(
                    f"{field} must be a list of strings: {relative_path}"
                )

    return catalog


def safe_artifact_path(root, relative_path):
    path = (root / relative_path).resolve()

    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise DegradationError(
            f"Artifact escapes evidence directory: {relative_path}"
        ) from error

    if path.is_symlink():
        raise DegradationError(
            f"Symbolic links are not permitted: {relative_path}"
        )

    return path


def alter_jsonl_records(path, record_ids, remove=False):
    if not record_ids:
        return 0

    if path.suffix.lower() != ".jsonl":
        raise DegradationError(
            f"Record-level operations require JSONL: {path.name}"
        )

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise DegradationError(
            f"Could not read {path.name}: {error}"
        ) from error

    output = []
    affected = 0
    found = set()

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise DegradationError(
                f"Invalid JSONL record at {path.name}:{line_number}"
            ) from error

        if not isinstance(record, dict):
            raise DegradationError(
                f"JSONL record must be an object: {path.name}"
            )

        record_id = record.get("record_id", record.get("event_id"))

        if record_id in record_ids:
            found.add(record_id)

            if remove:
                affected += 1
                continue

            timestamp = record.get("timestamp")

            if not isinstance(timestamp, str):
                raise DegradationError(
                    f"Record {record_id} has no timestamp."
                )

            try:
                parsed = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )

                if parsed.tzinfo is None:
                    raise ValueError("Timezone missing")

                modified = parsed + timedelta(
                    seconds=TIMESTAMP_OFFSET_SECONDS
                )

                record["timestamp"] = modified.astimezone(
                    timezone.utc
                ).isoformat()

            except ValueError as error:
                raise DegradationError(
                    f"Invalid timestamp in record {record_id}"
                ) from error

            affected += 1

        output.append(
            json.dumps(record, sort_keys=True, ensure_ascii=False)
        )

    missing = set(record_ids) - found

    if missing:
        raise DegradationError(
            f"Catalog references missing record IDs in {path.name}: "
            f"{sorted(missing)}"
        )

    path.write_text(
        "\n".join(output) + ("\n" if output else ""),
        encoding="utf-8"
    )

    return affected


def apply_degradation(trial_directory, source_relative, level):
    if level not in LEVELS:
        raise DegradationError(f"Unknown degradation level: {level}")

    trial = Path(trial_directory).resolve()

    if not trial.is_dir():
        raise DegradationError("Trial directory does not exist.")

    source = (trial / source_relative).resolve()

    try:
        source.relative_to(trial)
    except ValueError as error:
        raise DegradationError(
            "Source evidence must remain inside the trial."
        ) from error

    if not source.is_dir() or source == trial:
        raise DegradationError("Invalid source evidence directory.")

    if "ground_truth" in source.parts:
        raise DegradationError(
            "Ground truth must never be used as degradation input."
        )

    output = (
        trial / "evidence" / "host_degraded" / level
    ).resolve()

    try:
        output.relative_to(trial)
    except ValueError as error:
        raise DegradationError(
            "Output must remain inside the trial."
        ) from error

    if output == source or source in output.parents:
        raise DegradationError(
            "Output cannot be inside the source evidence directory."
        )

    if output.exists():
        raise DegradationError(
            f"Output already exists; refusing to overwrite: {output}"
        )

    catalog = load_catalog(source)

    for artifact in catalog["artifacts"]:
        path = safe_artifact_path(source, artifact["path"])

        if not path.is_file():
            raise DegradationError(
                f"Catalog artifact is missing: {artifact['path']}"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, output)

    operations = LEVELS[level]
    audit = []

    try:
        for artifact in catalog["artifacts"]:
            relative_path = artifact["path"]
            copied_path = safe_artifact_path(output, relative_path)

            if (
                "remove_noncritical" in operations
                and artifact["criticality"] == "noncritical"
            ):
                copied_path.unlink()

                audit.append({
                    "operation": "remove_noncritical",
                    "artifact": relative_path,
                    "status": "applied"
                })
                continue

            if (
                "shift_file_timestamps" in operations
                and artifact.get("timestamp_sensitive") is True
            ):
                old_stat = copied_path.stat()
                old_mtime = old_stat.st_mtime
                new_mtime = old_mtime + TIMESTAMP_OFFSET_SECONDS

                import os
                os.utime(
                    copied_path,
                    (old_stat.st_atime, new_mtime)
                )

                audit.append({
                    "operation": "shift_file_timestamps",
                    "artifact": relative_path,
                    "offset_seconds": TIMESTAMP_OFFSET_SECONDS,
                    "status": "applied"
                })

            if (
                "remove_log_records" in operations
                and artifact.get("removable_record_ids")
            ):
                affected = alter_jsonl_records(
                    copied_path,
                    artifact["removable_record_ids"],
                    remove=True
                )

                audit.append({
                    "operation": "remove_log_records",
                    "artifact": relative_path,
                    "records_affected": affected,
                    "status": "applied"
                })

            if (
                "alter_log_timestamps" in operations
                and artifact.get("alter_record_ids")
            ):
                affected = alter_jsonl_records(
                    copied_path,
                    artifact["alter_record_ids"],
                    remove=False
                )

                audit.append({
                    "operation": "alter_log_timestamps",
                    "artifact": relative_path,
                    "records_affected": affected,
                    "offset_seconds": TIMESTAMP_OFFSET_SECONDS,
                    "status": "applied"
                })

        result = {
            "schema_version": "1.0",
            "level": level,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_directory": str(source.relative_to(trial)),
            "output_directory": str(output.relative_to(trial)),
            "operations": operations,
            "audit": audit,
            "source_hashes": {},
            "output_hashes": {}
        }

        for artifact in catalog["artifacts"]:
            relative_path = artifact["path"]
            original = safe_artifact_path(source, relative_path)
            degraded = safe_artifact_path(output, relative_path)

            if original.is_file():
                result["source_hashes"][relative_path] = sha256_file(
                    original
                )

            if degraded.is_file():
                result["output_hashes"][relative_path] = sha256_file(
                    degraded
                )

        manifest_path = output / "degradation_manifest.json"

        manifest_path.write_text(
            json.dumps(result, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )

        return result

    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


if __name__ == "__main__":
    print("NARIS Degradation Engine")
    print("-" * 36)

    for level, operations in LEVELS.items():
        print(f"{level}: {operations}")

    print("\nNo evidence was modified.")
