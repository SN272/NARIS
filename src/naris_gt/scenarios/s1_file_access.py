
from pathlib import Path


SCENARIO = {
    "id": "S1",
    "name": "Unauthorized File Access and Simulated Exfiltration",
    "version": "1.0",

    "description": (
        "Controlled creation, access, reading, local staging, "
        "and network transfer of a synthetic test file from "
        "the Windows execution system to a designated Kali "
        "Linux laboratory receiver."
    ),

    "execution_host": "NARIS-Windows",
    "network_observer": "NARIS-Kali",

    "network": {
        "protocol": "HTTP",
        "source_ip": "192.168.56.20",
        "destination_ip": "192.168.56.10",
        "destination_port": 8080,
        "endpoint": "/s1-upload",
        "purpose": "Controlled synthetic file transfer"
    },

    "actions": [
        {
            "sequence": 1,
            "action": "create_test_file",
            "description": (
                "Create a synthetic confidential test file "
                "in the designated trial workspace."
            ),
            "expected_host_evidence": [
                "file_creation_metadata",
                "file_size",
                "file_sha256"
            ],
            "expected_network_evidence": []
        },
        {
            "sequence": 2,
            "action": "access_file",
            "description": (
                "Access the designated synthetic test file "
                "and record its available metadata."
            ),
            "expected_host_evidence": [
                "file_access_audit",
                "file_metadata"
            ],
            "expected_network_evidence": []
        },
        {
            "sequence": 3,
            "action": "read_file",
            "description": (
                "Read the contents of the synthetic test file "
                "and record the bytes read and file hash."
            ),
            "expected_host_evidence": [
                "process_execution_artifact",
                "file_access_audit",
                "file_sha256",
                "bytes_read"
            ],
            "expected_network_evidence": []
        },
        {
            "sequence": 4,
            "action": "stage_file_transfer",
            "description": (
                "Copy the synthetic test file into the "
                "controlled local transfer-staging directory "
                "and verify the source and staged hashes."
            ),
            "expected_host_evidence": [
                "staged_file_metadata",
                "source_sha256",
                "staged_sha256"
            ],
            "expected_network_evidence": []
        },
        {
            "sequence": 5,
            "action": "transfer_file",
            "description": (
                "Transfer the staged synthetic file over HTTP "
                "to the controlled Kali Linux laboratory receiver."
            ),
            "expected_host_evidence": [
                "transfer_process",
                "transfer_timestamp",
                "transfer_outcome"
            ],
            "expected_network_evidence": [
                "pcap_capture",
                "http_request_metadata",
                "source_destination",
                "transfer_timestamp",
                "transferred_byte_count",
                "receiver_sha256"
            ]
        }
    ]
}


def validate_s1_workspace(workspace):
    """
    Validate that the S1 workspace is an existing directory.

    This function does not create, delete, or modify files.
    """
    workspace = Path(workspace).resolve()

    if not workspace.exists():
        raise FileNotFoundError(
            f"S1 workspace does not exist: {workspace}"
        )

    if not workspace.is_dir():
        raise NotADirectoryError(
            f"S1 workspace is not a directory: {workspace}"
        )

    return workspace


def get_s1_action_plan():
    """
    Return the ordered S1 action plan.

    No incident actions are executed by this function.
    """
    return {
        "scenario_id": SCENARIO["id"],
        "scenario_name": SCENARIO["name"],
        "scenario_version": SCENARIO["version"],
        "execution_host": SCENARIO["execution_host"],
        "network_observer": SCENARIO["network_observer"],
        "network": SCENARIO["network"],
        "actions": SCENARIO["actions"]
    }


def validate_s1_definition():
    """
    Validate the internal consistency of the S1 definition.
    """
    actions = SCENARIO["actions"]

    if len(actions) != 5:
        raise ValueError(
            "S1 must contain exactly five controlled actions."
        )

    expected_sequences = list(range(1, 6))

    actual_sequences = [
        action["sequence"] for action in actions
    ]

    if actual_sequences != expected_sequences:
        raise ValueError(
            "S1 action sequences must be consecutive from 1 to 5."
        )

    expected_actions = [
        "create_test_file",
        "access_file",
        "read_file",
        "stage_file_transfer",
        "transfer_file"
    ]

    actual_actions = [
        action["action"] for action in actions
    ]

    if actual_actions != expected_actions:
        raise ValueError(
            "S1 action sequence does not match the frozen design."
        )

    if SCENARIO["network"]["protocol"] != "HTTP":
        raise ValueError(
            "S1 network transfer must use the defined HTTP protocol."
        )

    if not SCENARIO["network"]["endpoint"].startswith("/"):
        raise ValueError(
            "S1 network endpoint must begin with '/'."
        )

    if not any(
        action["action"] == "transfer_file"
        and action["expected_network_evidence"]
        for action in actions
    ):
        raise ValueError(
            "S1 must define independent network evidence."
        )

    return True


if __name__ == "__main__":
    validate_s1_definition()

    plan = get_s1_action_plan()

    print("NARIS S1 SCENARIO")
    print("-" * 48)

    print(f"Scenario: {plan['scenario_name']}")
    print(f"Version: {plan['scenario_version']}")
    print(f"Execution host: {plan['execution_host']}")
    print(f"Network observer: {plan['network_observer']}")

    print("\nNetwork transfer configuration:")

    for key, value in plan["network"].items():
        print(f"{key}: {value}")

    print("\nPlanned actions:")

    for action in plan["actions"]:
        print(
            f"{action['sequence']}. "
            f"{action['action']} - "
            f"{action['description']}"
        )

    print("\nS1 scenario definition: VALID")
    print("No incident actions were executed.")
