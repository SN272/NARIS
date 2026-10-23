# NARIS: Network-Assisted Detection and Reconstruction of Cyber Incidents under Anti-Forensic Conditions

## Project objective

NARIS investigates whether independent network evidence can improve the reconstruction of cyber incidents when host artifacts have been deleted, altered, or otherwise degraded by anti-forensic activity.

The experiment will establish ground truth in a controlled virtual lab, collect host and network evidence, apply defined levels of evidence degradation, and compare reconstruction using host-only, network-only, and combined evidence.

## Planned workflow

1. Establish and document the isolated virtual lab.
2. Create repeatable benign incident scenarios with recorded ground truth.
3. Capture network traffic independently of host artifacts.
4. Collect host artifacts and analyze them with appropriate forensic tools.
5. Apply controlled anti-forensic degradation levels.
6. Build and correlate timelines.
7. Compare reconstruction outcomes across evidence conditions and repeated trials.

## Lab baseline

The lab uses Kali Linux and Windows guests connected through a VirtualBox Internal Network named `naris-intnet`. The currently recorded addresses are Kali `192.168.56.10/24` and Windows `192.168.56.20/24`. Exact configuration and verification notes are maintained in [`docs/environment.md`](docs/environment.md).

## Repository structure

```text
NARIS-Research/
├── .gitignore
├── README.md
└── docs/
    └── environment.md
```

As the project develops, scripts, experiment configuration, sanitized example data, analysis code, and results documentation may be added in dedicated folders.

## Reproducibility policy

- Record exact tool versions, configuration, commands, and observed outputs.
- Separate intended configuration from verified behavior.
- Preserve ground truth independently from the evidence being evaluated.
- Use clean VM snapshots and repeatable procedures.
- Keep VM disks, installers, raw evidence, secrets, and other large or sensitive artifacts out of Git by default.
- Do not claim complete network isolation until the VM adapter configuration and relevant connectivity tests have been verified.

## Current status

- [x] Kali and Windows VMs created.
- [x] Baseline snapshots and descriptions recorded from VirtualBox.
- [x] Static lab addresses configured.
- [x] Kali-to-Windows ping previously verified.
- [x] Initial documentation committed and pushed.
- [x] Kali OS, kernel, packet-analysis tool, Python, and SHA-256 utility versions recorded.
- [x] Host hardware, VM resource allocations, guest IPs, adapters, and snapshot inventory recorded.
- [ ] Resolve Windows guest identity discrepancy before formal experiments.
- [ ] Review firewall scope and validate the isolation model before formal experiments.
- [ ] Implement the ground-truth engine.
- [ ] Implement repeatable evidence collection and reconstruction experiments.

## Safety and research integrity

Run experiments only on systems and networks you own or are authorized to test. Use isolated lab networking, retain baseline snapshots, and document each experimental change. Do not treat the host evidence being evaluated as the sole source of ground truth.
