
SCENARIO = {
    "id": "S2",
    "name": "Suspicious Process Execution and Persistence",
    "version": "1.0",
    "description": (
        "Controlled execution of a benign process and creation "
        "of a temporary, identifiable Windows persistence artifact "
        "for forensic investigation."
    ),
    "execution_host": "NARIS-Windows",
    "actions": [
        {
            "sequence": 1,
            "action": "create_test_script",
            "description": (
                "Create a harmless script that produces a "
                "recognisable execution marker."
            )
        },
        {
            "sequence": 2,
            "action": "execute_test_process",
            "description": (
                "Execute the benign test script and record "
                "process information."
            )
        },
        {
            "sequence": 3,
            "action": "create_persistence_artifact",
            "description": (
                "Create a controlled, identifiable Windows "
                "Run-key persistence entry."
            )
        },
        {
            "sequence": 4,
            "action": "verify_persistence_artifact",
            "description": (
                "Verify the registry entry and record its "
                "location and configured command."
            )
        }
    ]
}


def get_s2_action_plan():
    """Return the ordered S2 plan without executing any actions."""
    return {
        "scenario_id": SCENARIO["id"],
        "scenario_name": SCENARIO["name"],
        "scenario_version": SCENARIO["version"],
        "execution_host": SCENARIO["execution_host"],
        "actions": SCENARIO["actions"]
    }


if __name__ == "__main__":
    plan = get_s2_action_plan()

    print("NARIS S2 SCENARIO")
    print("-" * 42)
    print(f"Scenario: {plan['scenario_name']}")
    print(f"Version: {plan['scenario_version']}")
    print(f"Execution host: {plan['execution_host']}")

    print("\nPlanned actions:")
    for action in plan["actions"]:
        print(
            f"{action['sequence']}. "
            f"{action['action']} - "
            f"{action['description']}"
        )

    print("\nScenario definition loaded.")
    print("No incident actions were executed.")
