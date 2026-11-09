POC8 PCIe Gen2 x1 NVMe candidate — 2026-11-09

Based on POC7, which passed user board Gen1 x1 TS256GMTE400S detection, FAT read-only mount/list, kernel8.img complete read and unmount. Reported kernel8.img SHA256: 55ea30cbb9fba29fd9fe8438a5324c715904116450c6f7169219c4d2b92d9dca (no independent reference comparison yet).

POC8 changes PCIe max link speed from Gen1 to Gen2 (5 GT/s), keeping one lane. Clock source, power/reset, U-Boot POC1a, original DDR timing and SD boot remain the same. M.2 diagnostic additionally reports current/max link speed/width from sysfs.
Gen2 is a requested target, not a validated negotiated speed. Hardware link training may fall back to Gen1; check actual speed before claiming success.

Image: openwrt-25.12.6-mys-8mmx-v2-sd-nvme-poc8.img.gz
Back up SD configuration/data, verify SHA256SUMS.txt, write whole SD image and enable writer readback verification. Keep POC7 as rollback baseline. Do not write this image to the NVMe SSD.
Power off before handling M.2 SSD. Board SSD: Transcend TS256GMTE400S 256GB 2242 NVMe, existing Raspberry Pi partitions must be preserved.

After boot:
  cat /etc/myir-build
  myir-m2-diag
Expected: PCIe Gen.2 x1 link up, negotiated 5 GT/s x1, nvme0 controller live and nvme0n1 partitions. If speed stays 2.5 GT/s, Gen2 has not passed.

Read-only repeat of known FAT partition:
  mkdir -p /mnt/nvme
  mount -t vfat -o ro /dev/nvme0n1p1 /mnt/nvme
  sha256sum /mnt/nvme/kernel8.img
  umount /mnt/nvme
Expected hash above if the file is unchanged. Do not format or write SSD. Repeat diagnostics after reading to check for AER/I/O/reset/link errors. Actual Gen2 performance and long-term stability remain pending.

Fresh wired LAN uses DHCP and Wi-Fi starts disabled until configured. Initial password remains in the separately held private INITIAL-ACCESS.txt. No root credentials are published to Git.
RTC battery retention, NOR boot, NVMe write/endurance tests remain deferred.