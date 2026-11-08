# Hardware validation status

POC6 baseline: user-reported successful boot, previous wired DHCP/SSH/LuCI and Wi-Fi AP operation; RTC read/write/time advancement passed with the RX8025T driver. USB Type-A read tested previously; POC6 USB Type-C enumerated 32GB media, read-only FAT mount/list, full Image SHA256 and unmount passed. No USB write/endurance claim. RTC backup retention has not been tested because a battery was not fitted. NOR boot work is deferred.

Hardware tests are user-run with serial output supplied to the project. Offline user-mode tests do not emulate the kernel or peripheral electrical behavior.

## POC7 — 2026-11-08

Offline: compiled PCIe x1 Gen1/CPU clock output/reset/supply/NVMe autoload checked; tools run under ARM64 emulation; SSH/rpcd/LuCI HTTP/HTTPS passed; final FAT/ext4 partition readback and checks passed; 913 regular rootfs files equal the tested archive.

User board DIAG without SSD: Linux 6.12.113 booted, 00:00.0 Root Port registered, nvme/nvme_core loaded. `Phy link never came up`, `DLActive-`, no NVMe namespace: expected for an empty slot. LnkSta 2.5GT/s x1 alone is not evidence of link-up. `lspci` reported inability to load libkmod resources; PCI config output was available. Endpoint/SSD and actual I/O remain pending.

Planned SSD: Transcend TS256GMTE400S 256GB M.2 2242 NVMe PCIe Gen3 x4. POC7 starts at Gen1 x1 for bring-up; board hardware upper limit is Gen2 x1. Power off before fitting SSD. First test: `myir-m2-diag`, namespace detection, then read-only existing files. No formatting or writes.
