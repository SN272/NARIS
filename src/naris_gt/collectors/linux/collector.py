
import datetime
import json
import platform
import socket
import subprocess
import urllib.request
from pathlib import Path


SERVER_URL = "http://192.168.57.1:8765/collect"


def read_os_release():
    """Read Linux distribution details from /etc/os-release."""
    values = {}

    try:
        with open("/etc/os-release", "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"').strip("'")

    except OSError:
        pass

    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "distribution": values.get("PRETTY_NAME", "Unknown")
    }


def get_cpu_model():
    """Get the CPU model from /proc/cpuinfo."""
    cpuinfo = Path("/proc/cpuinfo")

    try:
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            if line.lower().startswith(("model name", "hardware")):
                return line.split(":", 1)[-1].strip()

    except OSError:
        pass

    return platform.processor() or "Unknown"


def get_memory():
    """Collect memory information from /proc/meminfo."""
    memory = {}

    try:
        for line in Path("/proc/meminfo").read_text(
            encoding="utf-8"
        ).splitlines():

            parts = line.split()

            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                memory[key] = int(parts[1])

    except (OSError, ValueError):
        pass

    return memory


def get_network_interfaces():
    """Collect interface names, MAC addresses, states, and IP addresses."""
    interfaces = []

    try:
        result = subprocess.run(
            ["ip", "-j", "address", "show"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        interface_data = json.loads(result.stdout)

        for item in interface_data:
            addresses = []

            for address in item.get("addr_info", []):
                local_address = address.get("local")

                if local_address:
                    addresses.append({
                        "address": local_address,
                        "prefix_length": address.get("prefixlen"),
                        "family": address.get("family"),
                        "scope": address.get("scope")
                    })

            interfaces.append({
                "interface": item.get("ifname", "unknown"),
                "mac_address": item.get("address"),
                "state": item.get("operstate", "unknown"),
                "ip_addresses": addresses
            })

        return interfaces

    except (
        FileNotFoundError,
        subprocess.SubprocessError,
        json.JSONDecodeError
    ):
        pass

    # Fallback if the ip command or JSON output is unavailable.
    net_path = Path("/sys/class/net")

    try:
        for interface_path in sorted(net_path.iterdir()):
            interface = interface_path.name

            try:
                mac_address = (
                    interface_path / "address"
                ).read_text(encoding="utf-8").strip()

                state = (
                    interface_path / "operstate"
                ).read_text(encoding="utf-8").strip()

            except OSError:
                mac_address = None
                state = "unknown"

            addresses = []

            try:
                result = subprocess.run(
                    ["ip", "-o", "address", "show", "dev", interface],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                for line in result.stdout.splitlines():
                    parts = line.split()

                    if "inet" in parts:
                        index = parts.index("inet")
                        addresses.append({
                            "address": parts[index + 1].split("/")[0],
                            "family": "inet"
                        })

                    elif "inet6" in parts:
                        index = parts.index("inet6")
                        addresses.append({
                            "address": parts[index + 1].split("/")[0],
                            "family": "inet6"
                        })

            except (FileNotFoundError, subprocess.SubprocessError):
                pass

            interfaces.append({
                "interface": interface,
                "mac_address": mac_address,
                "state": state,
                "ip_addresses": addresses
            })

    except OSError:
        pass

    return interfaces


def collect_system_information():
    """Build the system inventory record."""
    return {
        "schema_version": "1.1",
        "source": "kali",
        "hostname": socket.gethostname(),
        "collected_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "operating_system": read_os_release(),
        "hardware": {
            "processor": get_cpu_model(),
            "cpu_count": __import__("os").cpu_count(),
            "memory": get_memory()
        },
        "network_interfaces": get_network_interfaces()
    }


def submit_collection(experiment_id, token):
    """Submit the collected record to the NARIS controller."""
    record = collect_system_information()

    payload = {
        "experiment_id": experiment_id,
        "token": token,
        "source": "kali",
        "record": record
    }

    request = urllib.request.Request(
        SERVER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = response.read().decode("utf-8")
            print("Controller response:")
            print(result)

    except Exception as error:
        print(f"Collection submission failed: {error}")
        raise


if __name__ == "__main__":
    print("NARIS Kali Linux Collector")
    print("-------------------------")

    experiment_id = input("Enter experiment ID: ").strip()
    token = input("Enter collection token: ").strip()

    if not experiment_id or not token:
        raise SystemExit("Experiment ID and token are required.")

    submit_collection(experiment_id, token)
