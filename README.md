
# NARIS v1.0

## Network-Assisted Detection and Reconstruction of Cyber Incidents under Anti-Forensic Conditions

**Version:** 1.0  
**Project Type:** Research-focused experimental prototype  
**Research Domain:** Digital Forensics, Network Forensics and Anti-Forensics

---

## 1. Project Overview

NARIS (Network-Assisted Detection and Reconstruction of Cyber Incidents under Anti-Forensic Conditions) is a research-oriented system designed to investigate whether independent network evidence can improve the reconstruction of cyber incidents when host-based forensic evidence has been deleted, altered or otherwise degraded through anti-forensic techniques.

The system uses a controlled virtual laboratory to generate incident ground truth, collect host and network evidence independently, apply controlled levels of anti-forensic degradation to host evidence, and compare incident reconstruction using different evidence sources.

NARIS v1.0 focuses on establishing and experimentally evaluating this approach through one controlled cyber-incident scenario.

## 2. Research Objective

The primary objective is to evaluate the contribution of independent network evidence to cyber-incident reconstruction under increasing levels of host-evidence degradation.

### Research Question

To what extent does network evidence improve incident reconstruction completeness and accuracy as host evidence undergoes increasing levels of anti-forensic degradation?

### Experimental Comparison

Three reconstruction approaches are evaluated:

1. **Host-only reconstruction:** Uses host forensic evidence.
2. **Network-only reconstruction:** Uses independently captured network evidence.
3. **Combined reconstruction:** Uses both host and network evidence.

All reconstructed timelines are evaluated against independently recorded ground truth.

## 3. NARIS v1.0 Experimental Scope

NARIS v1.0 uses exactly one controlled incident scenario.

### S1 — Unauthorized File Access and Simulated Exfiltration

The scenario models a controlled file-access and simulated data-transfer incident in an isolated laboratory.

Planned activities include:

1. Creation of a synthetic confidential test file.
2. Access and reading of the test file.
3. Local staging of the file for transfer.
4. Controlled network transfer to a designated laboratory receiver.
5. Independent collection of host and network evidence.

The experiment uses Windows as the incident execution system and Kali Linux as the independent network observation system.

### Experimental Design

| Parameter | Configuration |
|---|---:|
| Scenarios | 1 |
| Scenario identifier | S1 |
| Degradation levels | 5 |
| Levels | L0, L1, L2, L3, L4 |
| Repetitions per level | 10 |
| Total experimental trials | 50 |
| Reconstruction modes | 3 |
| Planned reconstruction outputs | 150 |

The experiment consists of:

1 scenario × 5 degradation levels × 10 repetitions = 50 trials.

50 trials × 3 reconstruction modes = 150 reconstruction outputs.

## 4. Anti-Forensic Degradation Levels

The experiment uses five cumulative levels of host-evidence degradation.

| Level | Description |
|---|---|
| L0 | Baseline with no degradation |
| L1 | Removal of selected non-critical host evidence |
| L2 | L1 operations and controlled host timestamp modification |
| L3 | L2 operations and selected host log-record removal |
| L4 | L3 operations and alteration of selected host log timestamps |

Degradation is applied only to copies of original host evidence.

Original host evidence, independently captured network evidence and ground truth are preserved separately.

The actual effect of every degradation operation must be verified and documented.

## 5. Evidence Collection Architecture

### Host Evidence

Collected from the Windows incident execution system.

Potential evidence sources include:

- File-system artefacts.
- File metadata and timestamps.
- Process execution artefacts.
- Relevant Windows event logs.
- Other scenario-related host artefacts.

### Network Evidence

Collected independently through Kali Linux.

Potential evidence sources include:

- PCAP/PCAPNG captures.
- Network connection metadata.
- Source and destination addresses.
- Protocol and port information.
- Packet and request timestamps.
- Relevant transfer metadata.

### Ground Truth

Ground truth records the actual sequence of controlled incident activities.

It is stored separately from evidence used by reconstruction engines and is accessible only to the evaluation process.

Ground truth must not be used as an input to host-only, network-only or combined reconstruction.

## 6. Evaluation Methodology

Each reconstruction approach is evaluated against independently recorded ground truth.

The planned evaluation metrics are:

- Event precision.
- Event recall.
- Event F1-score.
- Reconstruction completeness.
- Timestamp error.
- Event-order accuracy.
- Evidence coverage.
- Missing-event rate.
- Conflict and uncertainty rate.

The evaluation will compare the performance of all three reconstruction approaches across L0–L4.

Statistical analysis will be conducted using the actual experimental outputs. No assumed or synthetic experimental results will be presented as findings.

## 7. Planned System Components

The v1.0 implementation is organised around the following components:

1. Controlled incident execution.
2. Ground-truth generation and integrity verification.
3. Host evidence collection.
4. Independent network evidence capture.
5. Evidence integrity and storage.
6. Anti-forensic degradation engine.
7. Host-only reconstruction.
8. Network-only reconstruction.
9. Combined reconstruction.
10. Ground-truth-based evaluation.
11. Statistical analysis.
12. Results visualisation and timeline generation.

A results-only Streamlit dashboard will present actual experimental findings. A Python-generated timeline diagram will visualise reconstructed incident events.

## 8. Laboratory Environment

The experimental environment uses VirtualBox with two isolated guest systems:

| System | Role | Address |
|---|---|---|
| Windows | Incident execution and host evidence collection | 192.168.56.20 |
| Kali Linux | Independent network observation | 192.168.56.10 |

The internal network is named `naris-intnet`.

Additional environment details, software versions, network configuration and baseline snapshots are documented in:

[`docs/environment.md`](docs/environment.md)

## 9. Repository Structure

```text
NARIS-Research/
│
├── config/
│   ├── experiment_matrix.json
│   └── targets.example.json
│
├── docs/
│   └── environment.md
│
├── src/
│   └── naris_gt/
│       ├── scenarios/
│       ├── collectors/
│       ├── ground_truth.py
│       ├── integrity.py
│       ├── records.py
│       ├── experiment_matrix.py
│       └── orchestrator.py
│
├── experiment_data/
├── pilot_data/
│
├── test_ground_truth.py
├── test_integrity.py
├── test_records.py
├── test_s1_importer.py
│
├── .gitignore
└── README.md
```

The structure will evolve as the reconstruction, evaluation, analysis and visualisation components are implemented.

## 10. Research Integrity and Reproducibility

NARIS follows these principles:

- Use only controlled and authorised laboratory experiments.
- Record actual experimental observations.
- Preserve original evidence.
- Keep ground truth independent from reconstruction inputs.
- Apply degradation only to designated evidence copies.
- Record failed trials rather than silently excluding them.
- Maintain evidence integrity through cryptographic hashing.
- Document software versions, configurations and experimental procedures.
- Do not fabricate or assume results.
- Keep raw forensic evidence and sensitive laboratory data outside public Git repositories.

## 11. Version Strategy

NARIS uses one project identity and repository with two clearly separated development versions.

### NARIS v1.0 — Research Prototype

The current version focuses on:

- One controlled scenario: S1.
- Five degradation levels: L0–L4.
- 50 genuine experimental trials.
- 150 reconstruction outputs.
- Three reconstruction approaches.
- Statistical evaluation.
- Results-only Streamlit dashboard.
- Python-generated reconstructed timeline diagram.

The research conclusions of v1.0 are limited to the S1 scenario and its experimental conditions.

### NARIS v2.0 — Expanded System

The future version is intended to introduce:

- Additional incident scenarios, including process persistence and remote access.
- Expanded anti-forensic techniques.
- Automated experiment execution and evidence collection.
- A larger independent experimental dataset.
- Improved evidence normalisation and correlation.
- Expanded reconstruction and statistical validation.

The v2.0 dataset and findings will remain separate from the v1.0 experimental dataset.

## 12. Current Development Status

### Completed

- [x] VirtualBox Windows and Kali laboratory established.
- [x] Internal network and host-only communication configured.
- [x] Baseline VM snapshots created.
- [x] Environment documentation established.
- [x] Repository and initial experiment architecture created.
- [x] Ground-truth recording foundation implemented.
- [x] Event validation and integrity mechanisms implemented.
- [x] Initial S1 host-side scenario execution completed.
- [x] One S1/L0 ground-truth trial imported and integrity-verified.
- [x] Initial S2 baseline work retained for future v2.0 development.

### In Progress

- [ ] Freeze and validate the v1.0 experiment design.
- [ ] Implement actual controlled network transfer in S1.
- [ ] Implement independent network capture and storage.
- [ ] Complete host evidence collection.
- [ ] Validate anti-forensic degradation on genuine evidence.
- [ ] Implement the three reconstruction modes.
- [ ] Implement ground-truth-based evaluation.

### Pending

- [ ] Complete 50 genuine experimental trials.
- [ ] Produce 150 reconstruction outputs.
- [ ] Perform statistical analysis.
- [ ] Generate publication-ready figures and tables.
- [ ] Build the results-only Streamlit dashboard.
- [ ] Generate reconstructed timeline visualisation.
- [ ] Finalise documentation and release NARIS v1.0.

A component is considered complete only after its outputs have been verified using actual experimental data.

## 13. Safety

All experiments are restricted to the controlled NARIS laboratory environment. Synthetic files, benign scripts and designated laboratory systems are used. No unauthorised external systems or networks are targeted.
