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

The lab uses Kali Linux and Windows guests connected through a VirtualBox Internal Network named `naris-intnet`. The recorded addresses are Kali `192.168.56.10/24` and Windows `192.168.56.20/24`. See [`docs/environment.md`](docs/environment.md) for the verified configuration, tool versions, snapshots, and outstanding limitations.

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

- [x] Kali and Windows VMs created and baseline snapshots recorded.
- [x] Static lab addresses configured and guest-to-guest connectivity previously verified.
- [x] Host hardware, VM resource allocations, guest IPs, adapter configuration, and snapshot inventory recorded.
- [x] Windows guest identity confirmed through Windows Settings as Windows 11 Home Single Language, version 26H2, build 26300.9457. The registry `ProductName` value reports Windows 10; this conflicting value is retained in the environment notes.
- [x] Kali OS, kernel, packet-analysis tool, Python, and SHA-256 utility versions recorded.
- [x] Host Git and Wireshark versions verified.
- [x] Windows Firewall state and ICMP rule scope recorded; the current rule is intentionally unchanged for now.
- [ ] Install and verify Autopsy and FTK Imager before using them in the workflow; Sysinternals Suite is downloaded but not yet configured/verified.
- [ ] Begin ground-truth event generation after remaining C1 readiness decisions are complete.
- [ ] Implement repeatable evidence collection, degradation, and reconstruction experiments.

## Safety and research integrity

Run experiments only on systems and networks you own or are authorized to test. Use isolated lab networking, retain baseline snapshots, and document each experimental change. Do not treat the host evidence being evaluated as the sole source of ground truth.
