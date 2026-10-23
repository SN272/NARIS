# NARIS
## Network-Assisted Detection and Reconstruction of Cyber Incidents under Anti-Forensic Conditions

NARIS is a digital forensics research project investigating whether independent network evidence can improve the reconstruction of cyber incidents when host-based forensic artifacts have been deleted, modified, or degraded.

## Research Objective

The project compares incident reconstruction using:

1. Host-based evidence alone.
2. Network-based evidence alone.
3. Correlated host and network evidence.

The objective is to evaluate which incident details remain recoverable under controlled levels of anti-forensic degradation.

## Research Methodology

The experimental environment uses isolated Windows and Kali Linux virtual machines. Controlled activities are generated with known ground truth, while network traffic and host artifacts are collected for subsequent forensic analysis.

The planned workflow is:

1. Configure and validate the isolated laboratory.
2. Generate controlled events and record ground truth.
3. Capture network traffic independently of host artifacts.
4. Collect and examine host-based evidence.
5. Apply controlled anti-forensic degradation.
6. Reconstruct incident timelines using host-only, network-only, and combined evidence.
7. Evaluate reconstruction accuracy and evidence loss across experimental conditions.

## Laboratory Architecture

| Component | Configuration |
|---|---|
| Host operating system | Windows 11 |
| Virtualization platform | Oracle VirtualBox 7.2.22 |
| Windows guest | Windows 11 Home Single Language |
| Kali guest | Kali Linux 2026.2 |
| Network type | VirtualBox Internal Network |
| Internal network name | `naris-intnet` |
| Windows lab IP | `192.168.56.20/24` |
| Kali lab IP | `192.168.56.10/24` |

The lab network is intended to isolate the guest machines from external networks. Network isolation and firewall configuration will be revalidated before experimental data collection.

## Repository Structure

- `README.md` — project overview, research objective, and workflow.
- `docs/environment.md` — laboratory configuration, versions, and validation.
- Additional directories for scripts, evidence-processing code, analysis, and results will be introduced as the project progresses.

## Reproducibility

The repository will preserve documentation, scripts, configuration details, analysis code, and non-sensitive experimental results required to understand and repeat the experiments.

Virtual machine disks, snapshots, installers, and raw evidence files are maintained separately from the source repository.

Snapshot availability alone is not considered sufficient for reproducibility. Rebuilding procedures, software versions, configuration details, and validation checks will also be documented.

## Current Status

- [x] Windows and Kali virtual machines created.
- [x] Clean-install snapshots created.
- [x] Static lab IP addresses configured.
- [x] Kali IP persistence verified after reboot.
- [x] Kali-to-Windows ICMP connectivity verified.
- [ ] Ground-truth event generation and validation.
- [ ] Network evidence capture.
- [ ] Host evidence collection.
- [ ] Anti-forensic experiments.
- [ ] Evidence correlation and reconstruction evaluation.

## Research Integrity

Ground truth, collected evidence, processing procedures, and reconstructed results will be distinguished explicitly. Experimental claims will be based on observed results rather than assumed tool capabilities.

## Safety

All experiments are intended for the controlled laboratory environment. No real incident data or unauthorized systems are required.
