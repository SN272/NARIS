# NARIS Laboratory Environment

## 1. Purpose

This document records the laboratory configuration used for the NARIS experiments. It supports setup verification, troubleshooting, and independent reconstruction of the environment.

## 2. Host and Virtualization

| Parameter | Recorded Value |
|---|---|
| Host operating system | Windows 11 |
| Virtualization platform | Oracle VirtualBox 7.2.22 |
| Windows guest | Windows 11 Home Single Language |
| Kali guest | Kali Linux 2026.2 |
| Windows VM memory | 4096 MB |
| Kali VM memory | 4096 MB |
| Kali virtual CPUs | 2 |
| Windows virtual disk | 80 GB, dynamically allocated |
| Kali virtual disk | Exact allocation to be verified |

Host hardware details, exact Windows build, Kali kernel version, and remaining VM settings will be added after verification.

## 3. Network Configuration

Both virtual machines use VirtualBox's Internal Network attachment.

| Parameter | Windows Guest | Kali Guest |
|---|---|---|
| Internal network | `naris-intnet` | `naris-intnet` |
| Network interface | Ethernet | `eth0` |
| IPv4 address | `192.168.56.20` | `192.168.56.10` |
| Prefix length | `/24` | `/24` |
| Default gateway | None configured for the lab interface | None configured for the lab interface |
| DNS | None configured for the lab interface | None configured for the lab interface |

The subnet is `192.168.56.0/24`. The guests use distinct static addresses.

The Kali address was configured through NetworkManager and was observed to persist after a reboot. Windows was configured with a static IPv4 address.

## 4. Network Validation

The following checks have been completed:

- Kali's interface `eth0` reported `192.168.56.10/24` after reboot.
- Kali sent four ICMP echo requests to `192.168.56.20`.
- All four requests received replies, with 0% packet loss.
- ARP requests from Kali previously received replies from the Windows guest.

These results validate basic guest-to-guest connectivity. They do not yet validate packet-capture completeness, network isolation under all conditions, or forensic reconstruction.

## 5. Firewall Considerations

Windows Firewall remains enabled. An inbound ICMPv4 Echo Request rule was enabled for the Private and Public profiles during connectivity troubleshooting; the Domain profile was left disabled.

Before evidence collection, review and narrow the rule to the active profile and the laboratory peer where possible. Do not disable Windows Firewall globally.

## 6. Baseline Snapshots

The following snapshots were reported as created:

- `C1-Windows-Clean-Install`
- `C1-Kali-Clean-Install`
- `C1-Network-Baseline` for Windows
- `C1-Network-Baseline` for Kali

Verify the snapshot names and descriptions in VirtualBox before a formal experiment. Snapshots are stored locally and are not committed to this repository.

## 7. Forensic Tools

| Tool | Status |
|---|---|
| Wireshark on host | Installed; version to be recorded |
| Git | Installed; version to be recorded |
| Autopsy 4.23.1 | Installer downloaded; installation not yet confirmed |
| FTK Imager 8.3.0.27 | Downloaded; installation not yet confirmed |
| Microsoft Sysinternals Suite | Downloaded; use and configuration not yet confirmed |
| Kali Wireshark | Available |
| Kali TShark | Available |
| Kali tcpdump | Available |
| Python 3 | Available; exact version to be recorded |

Tool availability does not imply that evidence collection or analysis has already been validated.

## 8. Reproduction Procedure

To recreate the current baseline:

1. Install the recorded VirtualBox version or document any version difference.
2. Create or import the Windows and Kali virtual machines using the documented guest versions and resource allocations.
3. Attach each guest's lab adapter to the Internal Network named `naris-intnet`.
4. Configure Windows as `192.168.56.20/24` and Kali as `192.168.56.10/24`.
5. Leave the lab interface without a default gateway or DNS server.
6. Keep host and guest firewall protections enabled, permitting only the traffic required for the experiment.
7. Start both guests and verify their interface addresses.
8. From Kali, run `ping -c 4 192.168.56.20` and record the output.
9. Record software versions, VM settings, snapshot identifiers, and validation results before beginning an experiment.

A clean rebuild must be validated independently. Restoring a snapshot is a recovery method, not proof that another researcher can reproduce the environment.

## 9. Known Limitations and Pending Records

- Exact host hardware specifications have not yet been recorded.
- Exact Windows build and Kali kernel versions remain to be recorded.
- Complete VirtualBox adapter settings and disk allocations must be verified.
- Host and network evidence collection pipelines have not yet been validated.
- Ground-truth event logging has not yet been validated.
- No experimental reconstruction accuracy results are claimed at this stage.
