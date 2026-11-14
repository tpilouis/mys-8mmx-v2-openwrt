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

## Clean-build SD boot — 2026-11-14

User reports SD flashing and successful board boot for the MYIR-Clean rebuilt POC8 image (SHA256 b9f8525e4f4e2d4d1f853d4fccf5e82a055fd0f7227cccadbecab87a45c88e6b). Fresh source/toolchain build needed the documented feeds configuration reseed fix and used the separately supplied POC1a boot blob. Peripheral/network regression and endurance results were not supplied for this new image.

Clean-image follow-up, 2026-11-14: user reports DHCP client test PASS. SD boot and DHCP client validated; SSH/LuCI and peripheral regression remain unreported for this image.

Clean-image follow-up, 2026-11-14: user reports USB and SSD tests PASS. Port, speed, procedure, hashes and write/performance details were not supplied. This records functional pass only; it does not establish all-port coverage, Gen2 negotiation, write integrity or endurance for this image. SSH/LuCI, Wi-Fi and RTC regression remain unreported.

## From-source boot chain board result — 2026-11-14

User confirmed rebuilt boot SHA256 prefix 53ad61e8 and provided SPL/U-Boot/kernel logs. DDR calibration completed, 2 GiB detected, SD kernel/DTB loaded, Linux 6.12.113 mounted SD ext4 root and reached the OpenWrt root shell. Basic end-to-end boot PASS.

Limits: an earlier restart after boot.scr is still unexplained (manual power cycle vs automatic reset not confirmed); repeated-boot stability is not validated. PCIe reports PHY link never came up and no NVMe endpoint; whether an SSD was inserted is unknown. Ethernet 100Mbps link and USB hub initialization were observed, not DHCP/device I/O tests. Wi-Fi generic firmware loaded with known CLM warning; RTC time invalid. These do not inherit prior images' peripheral PASS results. Root password was unset; set it locally before network use.

### Rebuilt boot chain: subsequent hardware validation (2026-11-14)

After inserting the SSD, the user supplied a successful Gen2 x1 (5.0 GT/s) boot with nvme0n1 p1/p2 enumeration. Read-only FAT mount, complete kernel8.img checksum and unmount passed; SHA256 55ea30cbb9fba29fd9fe8438a5324c715904116450c6f7169219c4d2b92d9dca matches previous reads. The user then reported 10/10 cold boots and 10/10 reboots passing for this new image. This supersedes the pending repeated-boot and SSD checks above; the cause of the earlier individual restart remains unknown. Long-duration stress, memory and other peripheral regression tests are not established by this report.

### Rebuilt boot chain: SSH login

The user set a root password and successfully logged in from Windows PowerShell using SSH password authentication to the current board address 192.168.50.138, reaching the OpenWrt root shell. SSH login PASS; no password/hash retained. This does not establish LuCI login or other remaining peripheral tests.

### Rebuilt boot chain: LuCI overview

User screenshot confirms authenticated LuCI system overview with Log out menu, correct MYIR POC8 model, OpenWrt 25.12.6 r0-71dbef3, Linux 6.12.113 and live system statistics. Browser URL uses HTTPS. Login and overview PASS; interface/wireless configuration pages and Wi-Fi functionality remain unconfirmed by this screenshot.

### Rebuilt boot chain: LuCI network pages and DHCP

User screenshots confirm Wireless and Interfaces pages render. Wireless lists radio0 but no active interface/station, so Wi-Fi functional test remains pending. Interfaces confirms lan DHCP client, carrier present, IPv4 192.168.50.138/24 and traffic counters: wired DHCP client PASS. The unused wwan has no device; this does not establish a radio failure.

### Rebuilt boot chain: USB-A read-only test

User output confirms USB storage on usb 2-1.1 behind the onboard hub, 32GB media with FAT32 bootfs at sdb1, read-only mount/list, full kernel8.img read (SHA256 49435997b1f076913dfe911ed5f8b27649876967c138969419abc6550790cdc6, read_exit=0) and unmount (exit=0). USB-A read test PASS. This is a different file version from the earlier NVMe test; no independent reference checksum comparison is claimed. Type-C and write/performance/endurance tests remain pending for this exact image.

### Rebuilt boot chain: Type-C Host read-only test

User output confirms the same 32GB media on usb 1-1 via Type-C OTG adapter, sdb1 FAT32 read-only mount, complete kernel8.img SHA256 49435997b1f076913dfe911ed5f8b27649876967c138969419abc6550790cdc6, read_exit=0 and unmount_exit=0. Type-C fixed Host read test PASS; checksum matches the USB-A read of the same file. Both USB-A and Type-C read regression tests are now complete for this image. Writes, measured throughput, endurance and USB device/gadget mode remain untested.

### Rebuilt boot chain: Wi-Fi AP association

User output confirms 2.4GHz channel 6 HT20 AP startup and a station with authorized/authenticated/associated yes, bidirectional packet counters and tx failed=0. AP authentication/association PASS. Reported 65.0 MBit/s is a PHY TX rate, not measured throughput. Phone DHCP and LuCI access over Wi-Fi remain to be confirmed; 5GHz/client/endurance remain untested and the known CLM warning persists. No Wi-Fi credentials are stored in this record.

### Rebuilt boot chain: phone LuCI access during AP test

Following the authorized AP station output, the user supplied a phone screenshot of authenticated LuCI overview at 192.168.50.138. This supports Wi-Fi AP basic management access PASS in the test sequence. Exact phone address/DHCP lease was not supplied; no separate DHCP lease evidence is claimed. RTC read/write/ticking remains pending for this new image.
