
import argparse
import hmac
import json
import uuid

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_ROOT = PROJECT_ROOT / "experiment_data" / "final_dataset"
MANIFEST_PATH = DATASET_ROOT / "batch_manifest.json"
UPLOAD_DIRECTORY = PROJECT_ROOT / "incoming_s1"

HOST = "192.168.57.1"
PORT = 8766
ALLOWED_CLIENT = "192.168.57.20"
MAX_UPLOAD_SIZE = 1_000_000

SCENARIO_ACTIONS = {
    "S1": [
        "create_test_file",
        "access_file",
        "read_file",
        "stage_file_transfer",
    ],
    "S2": [
        "create_test_script",
        "execute_test_process",
        "create_persistence_artifact",
        "verify_persistence_artifact",
    ],
}


def validate_trial(trial_id, scenario_id, level_id):
    if not MANIFEST_PATH.is_file():
        raise ValueError("Batch manifest not found.")

    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    matches = [
        trial for trial in manifest["trials"]
        if trial.get("trial_id") == trial_id
    ]

    if len(matches) != 1:
        raise ValueError("Trial ID is not in the prepared batch.")

    trial = matches[0]

    if trial.get("scenario_id") != scenario_id:
        raise ValueError("Trial scenario mismatch.")

    if scenario_id not in SCENARIO_ACTIONS or level_id != "L0":
        raise ValueError("Only registered S1/S2 L0 trials are enabled.")

    if trial.get("degradation_level_id") != level_id:
        raise ValueError("Trial degradation level mismatch.")

    return trial


class ScenarioUploadHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        endpoint_scenarios = {
            "/s1-upload": "S1",
            "/s2-upload": "S2",
        }

        expected_scenario = endpoint_scenarios.get(self.path)

        if expected_scenario is None:
            self.send_error(404)
            return

        if self.client_address[0] != ALLOWED_CLIENT:
            self.send_error(403, "Client not permitted")
            return

        supplied_token = self.headers.get("X-NARIS-Token", "")

        if not hmac.compare_digest(
            supplied_token,
            self.server.upload_token,
        ):
            self.send_error(403, "Invalid upload token")
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
        except ValueError:
            self.send_error(400, "Invalid content length")
            return

        if content_length <= 0 or content_length > MAX_UPLOAD_SIZE:
            self.send_error(413, "Invalid upload size")
            return

        try:
            raw_data = self.rfile.read(content_length)
            events = json.loads(raw_data.decode("utf-8-sig"))

            if not isinstance(events, list) or len(events) != 4:
                raise ValueError("Expected exactly four events.")

            if any(not isinstance(event, dict) for event in events):
                raise ValueError("Invalid event record.")

            trial_ids = {event.get("experiment_id") for event in events}
            scenario_ids = {event.get("scenario_id") for event in events}
            level_ids = {
                event.get("degradation_level_id") for event in events
            }
            run_ids = {event.get("run_id") for event in events}

            if len(trial_ids) != 1 or None in trial_ids:
                raise ValueError("Missing or inconsistent trial IDs.")

            if len(scenario_ids) != 1 or None in scenario_ids:
                raise ValueError("Missing or inconsistent scenario IDs.")

            if len(level_ids) != 1 or None in level_ids:
                raise ValueError("Missing or inconsistent degradation levels.")

            if len(run_ids) != 1 or None in run_ids:
                raise ValueError("Missing or inconsistent run IDs.")

            trial_id = next(iter(trial_ids))
            scenario_id = next(iter(scenario_ids))
            level_id = next(iter(level_ids))
            run_id = next(iter(run_ids))

            if scenario_id != expected_scenario:
                raise ValueError("Endpoint and scenario do not match.")

            validate_trial(trial_id, scenario_id, level_id)

            expected_actions = SCENARIO_ACTIONS[scenario_id]

            if [event.get("action") for event in events] != expected_actions:
                raise ValueError("Scenario action sequence is invalid.")

            if any(
                event.get("outcome") != "success"
                for event in events
            ):
                raise ValueError(
                    "Failed executions cannot enter the successful upload path."
                )

            if any(
                event.get("sequence") != index
                for index, event in enumerate(events, start=1)
            ):
                raise ValueError("Invalid event sequence.")

            if any(
                event.get("experiment_id") != trial_id
                or event.get("scenario_id") != scenario_id
                or event.get("degradation_level_id") != level_id
                or event.get("run_id") != run_id
                for event in events
            ):
                raise ValueError("Inconsistent event metadata.")

            UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

            filename = f"{uuid.uuid4()}.json"
            destination = UPLOAD_DIRECTORY / filename

            payload = {
                "received_at": datetime.now(timezone.utc).isoformat(),
                "source_ip": self.client_address[0],
                "trial_id": trial_id,
                "scenario_id": scenario_id,
                "degradation_level_id": level_id,
                "run_id": run_id,
                "event_count": len(events),
                "events": events,
            }

            temporary_path = destination.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(payload, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary_path.replace(destination)

            response = {
                "status": "received",
                "filename": filename,
                "trial_id": trial_id,
                "scenario_id": scenario_id,
                "event_count": len(events),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

            print(
                f"Received {len(events)} {scenario_id} events "
                f"for trial {trial_id}: {filename}"
            )

        except (
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            self.send_error(400, str(error))

    def log_message(self, format, *args):
        print(format % args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    if len(args.token) < 24:
        parser.error("Token must contain at least 24 characters.")

    server = HTTPServer((HOST, PORT), ScenarioUploadHandler)
    server.upload_token = args.token

    print("NARIS SCENARIO TRANSFER RECEIVER")
    print("-" * 42)
    print(f"Listening: {HOST}:{PORT}")
    print(f"Allowed client: {ALLOWED_CLIENT}")
    print("Enabled scenarios: S1/L0, S2/L0")
    print("Waiting for trial-bound execution logs...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReceiver stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
