
# NARIS v1.0 — Experimental Design

## 1. Research Objective

NARIS v1.0 investigates whether independent network evidence improves cyber-incident reconstruction when host-based evidence is subjected to controlled anti-forensic degradation.

The experiment compares host-only, network-only and combined reconstruction against independently recorded ground truth.

## 2. Scenario

### S1 — Unauthorized File Access and Simulated Exfiltration

A synthetic confidential file is created and processed on a controlled Windows system. The file is accessed, read, staged and transferred over HTTP to a designated Kali Linux receiver.

No external system or production data is involved.

## 3. Controlled Event Sequence

| Sequence | Event | Execution system |
|---|---|---|
| 1 | create_test_file | Windows |
| 2 | access_file | Windows |
| 3 | read_file | Windows |
| 4 | stage_file_transfer | Windows |
| 5 | transfer_file | Windows to Kali |

Each successful action is recorded in independent ground truth.

Failed and partial actions must also be recorded with their actual outcomes. They must not be represented as successful events.

## 4. Laboratory Configuration

| Component | Configuration |
|---|---|
| Incident execution system | Windows VM |
| Network observer and receiver | Kali Linux VM |
| Windows internal IP | 192.168.56.20 |
| Kali internal IP | 192.168.56.10 |
| Internal network | naris-intnet |
| Transfer protocol | HTTP |
| Transfer endpoint | /s1-upload |
| Transfer destination port | 8080 |

The incident transfer and research-control log transfer are separate operations.

Research-control uploads must not be treated as incident network evidence.

## 5. Ground Truth

Ground truth is recorded independently from forensic evidence.

Each event contains:

- event_id
- experiment_id
- scenario_id
- sequence
- timestamp
- action
- host
- process
- resource
- outcome
- details
- previous_event_hash
- event_hash

Ground-truth timestamps use UTC.

The details field may contain:

- run_id
- transfer_id
- source_sha256
- staged_sha256
- received_sha256
- bytes_transferred

Ground truth is available only to the evaluation component. It must not be supplied to reconstruction algorithms.

## 6. Host Evidence

Host evidence is collected from the Windows execution system.

Required collection targets:

- Original synthetic file and metadata.
- Staged synthetic file and metadata.
- File sizes and SHA-256 hashes.
- Relevant Windows Security object-access audit records.
- Relevant process execution records.
- Relevant PowerShell operational logs.
- Other available NTFS artefacts associated with the scenario.

Required auditing must be configured and verified before experimental collection.

Absence of an artefact must be recorded rather than replaced with assumed evidence.

## 7. Network Evidence

Kali Linux independently captures the controlled HTTP transfer.

Required collection targets:

- PCAP or PCAPNG packet capture.
- Source and destination IP addresses.
- Source and destination ports.
- HTTP method and endpoint.
- Transfer start and completion timestamps.
- Transferred byte count.
- Transfer identifier.
- Receiver-calculated SHA-256 hash.

The receiver must independently calculate the hash of the received file.

The original packet capture must be preserved and hashed.

## 8. Evidence Correlation

Evidence from different sources is correlated using:

- experiment_id
- scenario_id
- run_id
- transfer_id
- file SHA-256
- timestamps
- source and destination addresses

Correlation must not depend on ground-truth information being available to reconstruction algorithms.

Ground truth is used only after reconstruction, during evaluation.

## 9. Degradation Design

Five degradation levels are defined:

| Level | Planned operations |
|---|---|
| L0 | No degradation |
| L1 | Remove selected non-critical host evidence |
| L2 | L1 plus controlled host timestamp modification |
| L3 | L2 plus selected host log-record removal |
| L4 | L3 plus selected host log-timestamp alteration |

Degradation applies only to copies of host evidence.

Original host evidence, network captures and ground truth remain unchanged.

Every operation must record:

- source evidence path
- degraded evidence path
- operation performed
- affected artefact
- before and after hashes where applicable
- execution timestamp
- operation outcome

## 10. Reconstruction Modes

### Host-only

Uses only the permitted host evidence.

### Network-only

Uses only the independently captured network evidence.

### Combined

Uses both permitted host and network evidence.

None of the reconstruction modes may access ground truth.

## 11. Evaluation Metrics

All reconstruction outputs are evaluated against independent ground truth.

Metrics:

1. Event precision.
2. Event recall.
3. Event F1-score.
4. Reconstruction completeness.
5. Timestamp error.
6. Event-order accuracy.
7. Evidence coverage.
8. Missing-event rate.
9. Conflict and uncertainty rate.

Metric definitions and event-matching tolerances must be fixed before the complete dataset is generated.

## 12. Experimental Matrix

| Parameter | Value |
|---|---:|
| Scenarios | 1 |
| Degradation levels | 5 |
| Repetitions per level | 10 |
| Total trials | 50 |
| Reconstruction modes | 3 |
| Total reconstruction outputs | 150 |

## 13. Research Integrity

- Use synthetic test data only.
- Execute only in the controlled laboratory.
- Preserve original evidence.
- Keep ground truth separate.
- Never use ground truth as reconstruction input.
- Record failed trials.
- Do not fabricate missing artefacts or experimental results.
- Hash original and collected evidence.
- Keep raw evidence outside public Git repositories.

## 14. Scope Limitations

NARIS v1.0 evaluates one controlled file-access and simulated-exfiltration scenario.

Its findings must not be generalised to persistence, remote access, malware execution or other incident categories without additional experiments.

Those extensions are reserved for NARIS v2.0.
