# NARIS Lab Environment

## 1. Purpose

This document records the environment used for the NARIS research project, *Network-Assisted Detection and Reconstruction of Cyber Incidents under Anti-Forensic Conditions*. It distinguishes verified configuration from items that still require confirmation so that the experiment can be reproduced without overstating validation.

## 2. Host and virtualization

| Component | Recorded configuration | Status |
|---|---|---|
| Host operating system | Windows 10 Home Single Language; Windows build 26200; 64-bit | Verified with `Get-ComputerInfo` on 2026-10-23 |
| Virtualization platform | Oracle VirtualBox `7.2.22r175245` | Verified with `VBoxManage --version` |
| Kali guest | Kali GNU/Linux Rolling 2026.2, 64-bit | Verified from `/etc/os-release` |
| Kali kernel | `6.19.14+kali-amd64` | Verified from `uname -r` |
| Windows guest | Registry reports `Windows 10 Home Single Language`, display version `26H2`, build `26300`, UBR `9457`; 64-bit | Verified from guest registry; conflicts with VirtualBox guest profile and Windows 11 ISO filename; investigate before publication |
| Kali guest memory / vCPUs | 4096 MB / 2 vCPUs | Verified in VirtualBox VM configuration; guest reported 3917 MB physical memory |
| Windows guest memory / vCPUs | 4096 MB / 2 vCPUs | Verified in VirtualBox VM configuration |
| Host hardware | Lenovo model `21SUS4SJ00`; 13.67 GiB physical memory reported; AMD Ryzen 7 250 with Radeon 780M Graphics, 8 cores / 16 logical processors | Verified with `Get-CimInstance` on 2026-10-23 |
| Windows virtual disk | 81920 MiB virtual capacity; base VDI plus two differencing snapshot disks | Verified with `VBoxManage list hdds`; virtual capacity is not physical disk usage |
| Kali virtual disk | 82015 MiB virtual capacity; base VDI plus two differencing snapshot disks | Verified with `VBoxManage list hdds`; virtual capacity is not physical disk usage |

### Host details and Windows identity discrepancy

- Host manufacturer/model: Lenovo `21SUS4SJ00`.
- Host physical memory reported by Windows: 13.67 GiB.
- Host CPU: AMD Ryzen 7 250 with Radeon 780M Graphics; 8 cores and 16 logical processors.
- Host OS: Windows 10 Home Single Language, version `2009` as reported by `Get-ComputerInfo`, build `26200`, 64-bit.
- VirtualBox reports the Windows VM guest profile as `Windows 11 (64-bit)` and the mounted ISO filename is `Windows11_Client_x64_en-us_26300_9457.iso`. However, the guest registry reports `ProductName = Windows 10 Home Single Language`, `DisplayVersion = 26H2`, `CurrentBuild = 26300`, and `UBR = 9457`. The guest's `[System.Environment]::OSVersion.Version` reports `10.0.26300.0`, which alone does not distinguish Windows 10 from Windows 11. Preserve this discrepancy in the record; do not silently label the installed guest as Windows 11 until its identity is independently resolved.

## 3. Virtual network configuration

The two guests are intended to communicate over a VirtualBox **Internal Network** named `naris-intnet`.

| Guest/interface | IPv4 address | Prefix | Gateway/DNS |
|---|---|---|---|
| Kali `eth0` | `192.168.56.10` | `/24` | No default gateway shown; DNS not configured on the lab interface |
| Windows lab adapter | `192.168.56.20` | `/24` | No gateway/DNS configured on the lab interface |

### Kali network verification

Command: `ip -4 addr show eth0`

Observed address: `192.168.56.10/24`; interface state was `UP` and `LOWER_UP`.

Command: `ip route`

Observed route:

```text
192.168.56.0/24 dev eth0 proto kernel scope link src 192.168.56.10 metric 100
```

No default route appeared in this output. This is consistent with the intended lab-only routing configuration, but it does not independently prove complete network isolation.

A previous connectivity test from Kali to Windows (`ping -c 4 192.168.56.20`) returned 4 replies, 0% packet loss. ARP resolution was also previously observed.

### VirtualBox adapter and firewall notes

- Internal Network name: `naris-intnet`, verified for both VM adapters.
- Kali adapter: `eth0`, IPv4 `192.168.56.10/24`.
- Windows adapter: IPv4 `192.168.56.20/24`.
- Windows firewall remains enabled.
- The Windows inbound `File and Printer Sharing (Echo Request - ICMPv4-In)` rule was enabled for Private and Public profiles; Domain was left disabled. Review and narrow this rule to the active lab profile and peer where feasible before formal evidence collection.
- VirtualBox configuration showed adapter 1 attached to Internal Network `naris-intnet` for both guests; adapters 2–8 were disabled. Windows adapter promiscuous mode was `Deny`; cable connected was enabled. Do not claim complete isolation without reviewing the full configuration and any integration features.

## 4. Verified Kali tool versions

| Tool | Version / observed output | Verification command |
|---|---|---|
| Wireshark | `4.6.6` | `wireshark --version` |
| TShark | `4.6.6` | `tshark --version` |
| tcpdump | `4.99.6`; libpcap `1.10.6` | `tcpdump --version` |
| Python | `3.13.12` | `python3 --version` |
| SHA-256 utility | GNU coreutils `9.10` | `sha256sum --version` |
| Operating system | Kali GNU/Linux Rolling `2026.2` | `cat /etc/os-release` |
| Kernel | `6.19.14+kali-amd64` | `uname -r` |

Wireshark/TShark runtime information reported approximately 3917 MB physical memory and an AMD Ryzen 7 250 processor exposed to the guest. This is guest-reported runtime information, not a substitute for recording the host hardware specification.

## 5. Host tools and installers

| Tool | Recorded status | Notes |
|---|---|---|
| Git for Windows | Installed; version previously reported as `2.55.0.windows.3` | Repository initialized and pushed to GitHub |
| Host Wireshark | Installed; previously reported as `4.4.3` | Recheck host version if it will be used for research captures |
| Autopsy | Installer downloaded (`4.23.1`) | Installation/use not yet confirmed |
| FTK Imager | Installer downloaded (`8.3.0.27`) | Installation/use not yet confirmed |
| Microsoft Sysinternals Suite | Downloaded | Installation/use not yet confirmed |

Installers and VM assets are stored outside the Git source repository and should not be committed.

## 6. Snapshots

VirtualBox snapshot inventory recorded:

- Windows: `C1-Windows-Clean-Install` — fresh installation baseline; `C1-Network-Baseline` — clean network baseline, static IP `192.168.56.20/24`, `naris-intnet`, and pre-event baseline. Current snapshot: `C1-Network-Baseline`.
- Kali: `C1-Kali-Clean-Install` — fresh Kali baseline; `C1-Network-Baseline` — static IP `192.168.56.10/24` on `eth0`, `naris-intnet`, and NetworkManager persistence after reboot. Current snapshot: `C1-Network-Baseline`.

Snapshot names and descriptions were recorded from VirtualBox. Keep a clean baseline and take additional snapshots before controlled experimental changes.

## 7. Reproduction and validation procedure

1. Install the documented VirtualBox version and create/import the two guest VMs.
2. Configure a VirtualBox Internal Network named `naris-intnet` for the lab adapters.
3. Configure Kali as `192.168.56.10/24` and Windows as `192.168.56.20/24`.
4. Ensure the lab adapters have no default gateway or DNS server configured.
5. Verify Kali's address with `ip -4 addr show eth0` and routing with `ip route`.
6. Verify guest-to-guest connectivity with `ping -c 4 192.168.56.20` from Kali, accounting for the Windows firewall policy.
7. Inspect both VirtualBox VM network settings to confirm that only the intended lab adapter is attached during isolated experiments.
8. Record the exact Windows guest identity and resolve the noted product-name/ISO/profile discrepancy before formal trials.
9. Take clean baseline snapshots before introducing experimental activity.

## 8. Pending items and limitations

- Resolve the Windows guest identity discrepancy (registry product name says Windows 10, while the VM profile and ISO filename say Windows 11) before finalizing reproducibility claims.
- Verify whether host Wireshark `4.4.3` is still the current version if host captures will be used.
- Confirm installation and exact versions of Autopsy, FTK Imager, and Sysinternals before documenting them as installed tools.
- Review and narrow the Windows ICMP firewall rule where practical.
- Validate isolation with adapter inspection and controlled connectivity tests; do not infer complete isolation solely from the lack of a default route.

## 9. Research integrity

Record the commands, configuration, timestamps, and observed outputs used to validate the environment. Clearly distinguish intended configuration from measured results. Keep raw packet captures, memory images, disk images, VM disks, installers, and other large or sensitive artifacts outside the source repository unless there is an explicit, reviewed reason to publish sanitized samples.
