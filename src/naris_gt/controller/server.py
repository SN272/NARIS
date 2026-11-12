
import hashlib
import json
import os
import secrets
import sys
import uuid

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "naris_gt"))

from integrity import create_integrity_manifest, register_manifest


PILOT_DATA_ROOT = PROJECT_ROOT / "pilot_data" / "real_baseline"
REGISTRY_PATH = PROJECT_ROOT / "integrity_registry.json"

CONTROLLER_ADDRESS = "192.168.57.1"
CONTROLLER_PORT = 8765

EXPERIMENT_ID = None
AUTH_TOKEN = None
EXPERIMENT_DIR = None
RECEIVED_SOURCES = set()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    os.replace(temporary_path, path)


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_record_hash(record):
    canonical_record = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    return hashlib.sha256(canonical_record).hexdigest()


def initialise_experiment(experiment_id):
    global EXPERIMENT_ID
    global AUTH_TOKEN
    global EXPERIMENT_DIR
    global RECEIVED_SOURCES

    experiment_dir = PILOT_DATA_ROOT / experiment_id

    if experiment_dir.exists():
        raise FileExistsError(
            f"Experiment directory already exists: {experiment_dir}"
        )

    EXPERIMENT_ID = experiment_id
    AUTH_TOKEN = secrets.token_urlsafe(32)
    EXPERIMENT_DIR = experiment_dir
    RECEIVED_SOURCES = set()

    (EXPERIMENT_DIR / "collections").mkdir(
        parents=True,
        exist_ok=False
    )

    metadata = {
        "experiment_id": experiment_id,
        "dataset_role": "pilot",
        "scenario": "system_baseline_collection",
        "collection_type": "real_system_inventory",
        "created_at": utc_now(),
        "status": "collecting",
        "expected_sources": ["windows", "kali"],
        "received_sources": [],
        "total_collections": 0
    }

    config = {
        "experiment_id": experiment_id,
        "dataset_role": "pilot",
        "scenario": "system_baseline_collection",
        "targets": {
            "windows": "192.168.57.20",
            "kali": "192.168.57.10"
        },
        "controller": {
            "address": CONTROLLER_ADDRESS,
            "port": CONTROLLER_PORT
        }
    }

    save_json(EXPERIMENT_DIR / "metadata.json", metadata)
    save_json(EXPERIMENT_DIR / "experiment_config.json", config)

    return AUTH_TOKEN


def validate_submission(data):
    if not isinstance(data, dict):
        return False, "Request must contain a JSON object"

    if data.get("experiment_id") != EXPERIMENT_ID:
        return False, "Experiment ID mismatch"

    if data.get("token") != AUTH_TOKEN:
        return False, "Authentication failed"

    source = data.get("source")

    if source not in ("windows", "kali"):
        return False, "Unknown collection source"

    if source in RECEIVED_SOURCES:
        return False, f"{source} has already submitted data"

    record = data.get("record")

    if not isinstance(record, dict):
        return False, "Collection record is missing"

    if not record.get("hostname"):
        return False, "Hostname is missing"

    if not record.get("collected_at"):
        return False, "Collection timestamp is missing"

    return True, "Submission accepted"


def finalise_experiment():
    sources = sorted(RECEIVED_SOURCES)

    if set(sources) != {"windows", "kali"}:
        return

    events = []

    for sequence, source in enumerate(
        ["windows", "kali"],
        start=1
    ):
        record_path = (
            EXPERIMENT_DIR /
            "collections" /
            f"{source}.json"
        )

        record = load_json(record_path)

        event = {
            "experiment_id": EXPERIMENT_ID,
            "event_id": str(uuid.uuid4()),
            "sequence": sequence,
            "event_type": "system_inventory_collection",
            "action": "collect_system_inventory",
            "target": record["hostname"],
            "outcome": "success",
            "timestamp": record["collected_at"],
            "details": {
                "source": source,
                "record_file": f"collections/{source}.json",
                "record_sha256": calculate_record_hash(record)
            },
            "evidence_reference": f"collections/{source}.json"
        }

        events.append(event)

    save_json(
        EXPERIMENT_DIR / "collection_events.json",
        events
    )

    manifest = create_integrity_manifest(
        EXPERIMENT_ID,
        events
    )

    save_json(
        EXPERIMENT_DIR / "integrity.json",
        manifest
    )

    register_manifest(
        EXPERIMENT_ID,
        manifest,
        str(REGISTRY_PATH)
    )

    metadata_path = EXPERIMENT_DIR / "metadata.json"
    metadata = load_json(metadata_path)

    metadata["received_sources"] = sources
    metadata["total_collections"] = len(sources)
    metadata["total_events"] = len(events)
    metadata["status"] = "completed"
    metadata["completed_at"] = utc_now()
    metadata["integrity_status"] = "manifest_registered"

    save_json(metadata_path, metadata)

    print("\nPILOT BASELINE COLLECTION COMPLETE")
    print("Experiment:", EXPERIMENT_ID)
    print("Storage:", EXPERIMENT_DIR)
    print("Collections:", len(sources))
    print("Integrity manifest created and registered.")
    print("Dataset role: PILOT — excluded from final research dataset.")


class CollectionHandler(BaseHTTPRequestHandler):

    def send_json(self, status, response):
        body = json.dumps(response).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/collect":
            self.send_json(404, {"error": "Endpoint not found"})
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", 0)
            )

            if content_length <= 0 or content_length > 2_000_000:
                self.send_json(413, {"error": "Invalid request size"})
                return

            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            valid, message = validate_submission(data)

            if not valid:
                self.send_json(400, {"error": message})
                return

            source = data["source"]
            record = data["record"]

            save_json(
                EXPERIMENT_DIR / "collections" / f"{source}.json",
                record
            )

            RECEIVED_SOURCES.add(source)

            metadata_path = EXPERIMENT_DIR / "metadata.json"
            metadata = load_json(metadata_path)

            metadata["received_sources"] = sorted(RECEIVED_SOURCES)
            metadata["total_collections"] = len(RECEIVED_SOURCES)

            save_json(metadata_path, metadata)

            print(f"\nReceived collection from: {source}")
            print("Hostname:", record["hostname"])

            if len(RECEIVED_SOURCES) == 2:
                finalise_experiment()

            self.send_json(
                200,
                {
                    "status": "accepted",
                    "dataset_role": "pilot",
                    "source": source,
                    "experiment_id": EXPERIMENT_ID,
                    "received_sources": sorted(RECEIVED_SOURCES)
                }
            )

        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON"})

        except Exception as error:
            print("Collection error:", error)
            self.send_json(500, {"error": str(error)})

    def log_message(self, format, *args):
        print("[HTTP]", format % args)


def start_server():
    server = HTTPServer(
        (CONTROLLER_ADDRESS, CONTROLLER_PORT),
        CollectionHandler
    )

    print("\nNARIS PILOT BASELINE COLLECTION SERVER")
    print("Listening on:", f"http://{CONTROLLER_ADDRESS}:{CONTROLLER_PORT}")
    print("Experiment ID:", EXPERIMENT_ID)
    print("Storage:", EXPERIMENT_DIR)
    print("Dataset role: PILOT")
    print("\nWaiting for Windows and Kali collectors...")
    print("Press CTRL+C to stop the server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nNARIS server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    experiment_id = str(uuid.uuid4())

    token = initialise_experiment(experiment_id)

    print("\nNEW NARIS PILOT BASELINE")
    print("========================")
    print("Experiment ID:", experiment_id)
    print("Authentication token:", token)
    print("\nKeep this terminal open.")

    start_server()
