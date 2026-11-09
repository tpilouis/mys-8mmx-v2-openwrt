# Hardware validation status

POC6 baseline: user-reported successful boot, previous wired DHCP/SSH/LuCI and Wi-Fi AP operation; RTC read/write/time advancement passed with the RX8025T driver. USB Type-A read tested previously; POC6 USB Type-C enumerated 32GB media, read-only FAT mount/list, full Image SHA256 and unmount passed. No USB write/endurance claim. RTC backup retention has not been tested because a battery was not fitted. NOR boot work is deferred.

Hardware tests are user-run with serial output supplied to the project. Offline user-mode tests do not emulate the kernel or peripheral electrical behavior.

## POC7 — 2026-11-08

Offline: compiled PCIe x1 Gen1/CPU clock output/reset/supply/NVMe autoload checked; tools run under ARM64 emulation; SSH/rpcd/LuCI HTTP/HTTPS passed; final FAT/ext4 partition readback and checks passed; 913 regular rootfs files equal the tested archive.

User board DIAG without SSD: Linux 6.12.113 booted, 00:00.0 Root Port registered, nvme/nvme_core loaded. `Phy link never came up`, `DLActive-`, no NVMe namespace: expected for an empty slot. LnkSta 2.5GT/s x1 alone is not evidence of link-up. `lspci` reported inability to load libkmod resources; PCI config output was available. Endpoint/SSD and actual I/O remain pending.

Planned SSD: Transcend TS256GMTE400S 256GB M.2 2242 NVMe PCIe Gen3 x4. POC7 starts at Gen1 x1 for bring-up; board hardware upper limit is Gen2 x1. Power off before fitting SSD. First test: `myir-m2-diag`, namespace detection, then read-only existing files. No formatting or writes.

## POC7 SSD test — 2026-11-09

User test with TS256GMTE400S: PCIe Gen1 x1 link up, Root Port DLActive+, NVMe controller live, 256.06GB namespace and two partitions recognized. FAT32 nvme0n1p1 read-only mount/list/unmount passed. Complete kernel8.img read SHA256: `55ea30cbb9fba29fd9fe8438a5324c715904116450c6f7169219c4d2b92d9dca`; no independent reference comparison. Existing Raspberry Pi data retained. No NVMe writes or endurance test.

## POC8 Gen2 candidate — 2026-11-09

Only Root Port maximum link speed is changed to Gen2, with version markers and read-only sysfs link-speed diagnostics. Compiled DTBs compared against POC7: only model labels and intended speed property differ. Offline NVMe/tools/SSH/LuCI/FAT/ext4/gzip/913-file integrity checks passed. Physical Gen2 5GT/s x1 negotiation, read test and stability remain pending. If it negotiates 2.5GT/s, Gen2 has not passed. U-Boot, DDR timing, clock routing and power/reset unchanged. Keep POC7 as rollback.

## POC8 Gen2 board read test — 2026-11-09

Supersedes the pending negotiation/read status above. User board DIAG reports `PCIe Gen.2 x1 link up`; Root Port and SSD sysfs both report 5.0 GT/s, width 1. Root Port DLActive+, TS256GMTE400S controller live, 256.06GB namespace and existing FAT32/ext4 partitions recognized. AER status flags in the supplied snapshot do not show errors; this is not an endurance result.

User mounted `/dev/nvme0n1p1` with `-t vfat -o ro`, read the complete `kernel8.img` with sha256sum and unmounted successfully. SHA256: `55ea30cbb9fba29fd9fe8438a5324c715904116450c6f7169219c4d2b92d9dca`, identical to the prior Gen1 test on the same SSD/file. This is cross-speed read consistency, not an independent comparison to an original distribution image.

PASS: Gen2 x1 negotiation, NVMe/partition detection, FAT32 read-only mount, complete file read and unmount. No SSD formatting/write performed in this test. Write, measured throughput, repeated cold boots and long-term stability remain untested.
