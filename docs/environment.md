# NARIS Lab Environment

## 1. Purpose

This document records the environment used for the NARIS research project, *Network-Assisted Detection and Reconstruction of Cyber Incidents under Anti-Forensic Conditions*. It distinguishes verified configuration from items that still require confirmation so that the experiment can be reproduced without overstating validation.

## 2. Host and virtualization

| Component | Recorded configuration | Status |
|---|---|---|
| Host operating system | Windows 10 Home Single Language; Windows build 26200; 64-bit | Verified with `Get-ComputerInfo` on 2026-10-23 |
| Host hardware | Lenovo model `21SUS4SJ00`; 13.67 GiB physical memory reported; AMD Ryzen 7 250 with Radeon 780M Graphics, 8 cores / 16 logical processors | Verified with `Get-CimInstance` on 2026-10-23 |
| Virtualization platform | Oracle VirtualBox `7.2.22r175245` | Verified with `VBoxManage --version` |
| Kali guest | Kali GNU/Linux Rolling `2026.2`, 64-bit | Verified from `/etc/os-release` |
| Kali kernel | `6.19.14+kali-amd64` | Verified from `uname -r` |
| Windows guest | Windows 11 Home Single Language, version `26H2`, OS build `26300.9457` | Confirmed in Windows Settings → System → About; edition confirmed by DISM |
| Windows guest registry note | Registry `ProductName` reports `Windows 10 Home Single Language`, `DisplayVersion` `26H2`, build `26300`, UBR `9457` | Conflicts with Settings display; Settings, DISM edition, VirtualBox profile, and ISO filename identify Windows 11. Preserve this discrepancy for transparency. |
| Kali guest memory / vCPUs | 4096 MB / 2 vCPUs | Verified in VirtualBox VM configuration; guest reported about 3917 MB physical memory |
| Windows guest memory / vCPUs | 4096 MB / 2 vCPUs | Verified in VirtualBox VM configuration |
| Windows virtual disk | 81920 MiB virtual capacity; base VDI plus two differencing snapshot disks | Verified with `VBoxManage list hdds`; virtual capacity is not physical disk usage |
| Kali virtual disk | 82015 MiB virtual capacity; base VDI plus two differencing snapshot disks | Verified with `VBoxManage list hdds`; virtual capacity is not physical disk usage |

### Windows guest identity evidence

- Windows Settings → System → About shows **Windows 11 Home Single Language**, version `26H2`, OS build `26300.9457`; the displayed installation date is `22-10-2026`.
- `DISM /Online /Get-CurrentEdition` completed successfully and reported edition `CoreSingleLanguage` and image version `10.0.26300.9457`.
- VirtualBox guest profile is `Windows 11 (64-bit)`, and the mounted ISO filename is `Windows11_Client_x64_en-us_26300_9457.iso`.
- The registry `ProductName` value reports `Windows 10 Home Single Language`; `[System.Environment]::OSVersion.Version` reports `10.0.26300.0`. The `10.0` version format alone does not distinguish Windows 10 from Windows 11. The installed release is recorded as Windows 11 based on the Settings screen and corroborating edition/build context; the registry discrepancy remains noted rather than hidden.

## 3. Virtual network configuration

The two guests communicate over a VirtualBox **Internal Network** named `naris-intnet`.

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

A previous connectivity test from Kali to Windows (`ping -c 4 192.168.56.20`) returned 4 replies, 0% packet loss. ARP resolution was also previously observed. This test is recorded as already completed and should not be repeated unless a later configuration change makes it necessary.

### VirtualBox adapter and firewall notes

- Internal Network name: `naris-intnet`, verified for both VM adapters.
- Both VMs use Adapter 1 attached to `naris-intnet`; adapters 2–8 were disabled in the recorded configuration.
- Windows adapter: Intel PRO/1000 MT Desktop (`82540EM`), promiscuous mode `Deny`, cable connected.
- Kali adapter: Intel PRO/1000 MT Desktop (`82540EM`), cable connected.
- Windows Firewall is enabled for Domain, Private, and Public profiles.
- The inbound `File and Printer Sharing (Echo Request - ICMPv4-In)` rule has two profile-specific entries: enabled for `Private, Public`, and disabled for `Domain`; direction is inbound and action is Allow.
- The rule is intentionally being left unchanged for now. It permits ICMP echo requests on both Private and Public profiles; it is broader than a peer-restricted rule. Reconsider scoping to the Kali peer `192.168.56.10` if later experiments require tighter least-privilege controls.
- Both lab adapters have no default gateway configured. These settings and prior connectivity checks support the intended lab topology but do not prove every aspect of isolation. Do not claim complete isolation solely from adapter inspection or the absence of a default route.

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

Wireshark/TShark runtime information reported approximately 3917 MB physical memory and an AMD Ryzen 7 250 processor exposed to the guest. This is guest-reported runtime information, not a substitute for the host hardware specification.

## 5. Host tools and installers

| Tool | Recorded status | Notes |
|---|---|---|
| Git for Windows | Installed; uninstall registry reports `2.55.0.3`; command-line version previously reported as `2.55.0.windows.3` | Repository is hosted at `https://github.com/SN272/NARIS.git`; documentation commit `5f3bdf3` was successfully pushed to `main` before this update |
| Host Wireshark | Installed, `4.6.7 x64` | Verified from Windows uninstall registry on 2026-10-23; use this version for host captures if host capture is part of the method |
| Autopsy | Installer downloaded (`4.23.1`); not installed | Common path `C:\Program Files\Autopsy` was checked and not found; installation remains pending |
| FTK Imager | Installer downloaded (`8.3.0.27`); not installed | Common path `C:\Program Files\FTK Imager` was checked and not found; installation remains pending |
| Microsoft Sysinternals Suite | Downloaded; not installed/configured or verified for use | Portable utilities may not require a conventional installer; verify the extracted tools when needed |

The uninstall-registry query did not find Autopsy or FTK Imager, and the user confirmed that only the installers were downloaded. VM assets, installers, and evidence are stored outside the source repository and should not be committed.

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
6. If configuration changes make it necessary, verify guest-to-guest connectivity from Kali to Windows, accounting for Windows Firewall policy. This check has already been completed for the current baseline.
7. Inspect both VirtualBox VM network settings to confirm that only the intended lab adapter is attached during isolated experiments. This inspection has already been completed for the current baseline.
8. Record Windows identity evidence from Settings, DISM, and registry; retain the noted registry `ProductName` discrepancy.
9. Take clean baseline snapshots before introducing experimental activity.

## 8. Pending items and limitations

- Install and verify Autopsy before the host-artifact analysis stage.
- Install and verify FTK Imager before using it to acquire or inspect forensic images.
- Verify the extracted Sysinternals utilities if they are needed for host artifact collection.
- Keep the current Windows ICMP firewall rule unchanged for now; consider restricting it to the Kali peer if later experimental requirements justify that change.
- Validate capture completeness and the isolation model as part of the actual evidence-collection workflow. Adapter inspection and the absence of a default route do not alone establish complete isolation.
- Ground-truth event generation, evidence collection pipelines, anti-forensic scenarios, and reconstruction accuracy evaluation have not yet been implemented/validated. No experimental reconstruction accuracy results are claimed at this stage.

## 9. Research integrity

Record the commands, configuration, timestamps, and observed outputs used to validate the environment. Clearly distinguish intended configuration from measured results. Keep raw packet captures, memory images, disk images, VM disks, installers, and other large or sensitive artifacts outside the source repository unless there is an explicit, reviewed reason to publish sanitized samples.
