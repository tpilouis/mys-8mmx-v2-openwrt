# MYIR MYS-8MMX-V2 OpenWrt

Private board bring-up project maintained by Louis Chou. Board: MYS-8MMX-V2, PCB V10, i.MX8MM Quad / 2 GiB DDR4. This repository is a pinned OpenWrt port kit, not a fork containing the full upstream history. It preserves the local POC6 baseline and subsequent POC7/POC8 changes in separate commits/tags.

## Current snapshot: POC8 PCIe Gen2 x1 read-validated

OpenWrt maintenance commit `71dbef3fd854850a810c93416c16d32d3fc82734`, Linux 6.12.113; feeds are pinned in `configs/feeds.conf`. The OpenWrt label remains 25.12.6 with local maintenance changes; this is not an official supported device image.

- SD boot uses U-Boot 2025.04 MYIR POC1a and original vendor DDR timing; the complete workflow below builds the boot chain from pinned sources.
- Wired LAN DHCP client, SSH/LuCI, AP6256 Wi-Fi, RX8025T RTC, USB-A and fixed-Host USB Type-C.
- POC6 Type-C read-only FAT mount and complete 35,373,568-byte Image read passed on board; SHA256 `7880ec0586b87ae7fc391373594a2cd871334154aad9b4c62e57dec79cf6c38f`; unmount passed.
- RTC battery retention, NOR boot and USB write/endurance tests remain deferred.

POC7 adds PCIe x1 Gen1 with CPU-sourced reference clock, NVMe driver/autoload, pciutils/nvme-cli and `myir-m2-diag`. Offline validation passed. Board boot without SSD passed: Root Port registered, NVMe modules loaded, no endpoint/link (expected with an empty socket). On 2026-11-09, TS256GMTE400S 256GB enumeration, Gen1 x1 link, FAT32 read-only mount/list, complete kernel8.img read and unmount passed. Independent reference hash comparison and write/endurance tests remain pending. See `docs/HARDWARE-STATUS.md`.

POC8 raises the PCIe target from Gen1 x1 to Gen2 x1 (5 GT/s) and adds sysfs negotiated-speed diagnostics. Compiled DTB comparison confirms only model labels and the Root Port speed change. Offline checks passed. On 2026-11-09 the user verified Gen2 x1 (5 GT/s) on both Root Port and SSD, live NVMe controller/partitions, FAT32 read-only mount, complete kernel8.img read and unmount. The file SHA256 matches the prior Gen1 read. Write, throughput and long-term stability tests remain pending. Keep POC7 as the read-tested rollback baseline. See `docs/POC8-GEN2-TEST.md`.

## Contents

`patches/myir.patch` applies to the pinned OpenWrt commit. `overlay/` contains runtime files, `configs/` build/feeds pins, `tools/` original build and verification scripts plus a portable source-preparation script, and `validation/` historical local artifact reports. Reports describe the original local builds; they are not evidence that a build made from this export has passed those tests. Image checksums in the reports reference artifacts intentionally excluded from Git.

## Beginner guide

Windows/WSL2 step-by-step instructions and the live clean-build verification record: [新手乾淨建置操作手冊](docs/BEGINNER-CLEAN-BUILD.zh-TW.md). See its status table for completed versus pending stages.

## Complete from-source SD workflow

After installing Git, Python 3 and Docker on Ubuntu/WSL (uid 1000), read [the NXP firmware notice](bootloader/NXP-FIRMWARE-NOTICE.md). If you accept the applicable agreement:

```sh
bash tools/build-sd.sh --accept-nxp-eula
```

This builds pinned OpenWrt, SPL/U-Boot, TF-A and imx-mkimage, obtains hash-verified proprietary DDR firmware, and composes/checks the SD image in `output/from-zero`. No externally supplied boot blob is required. The board patch and original GPL DDR timing are in `bootloader/`; no proprietary firmware payloads are stored in Git. See [開機元件從零建置手冊](docs/BOOTLOADER-FROM-SOURCE.zh-TW.md) for consent, versions, outputs and tests. No storage device is flashed automatically.

The component builds and both wrapper modes have passed offline checks in MYIR-Clean; the newly rebuilt boot blob differs from the old prebuilt artifact. On 2026-11-14 it reached the OpenWrt shell and passed PCIe Gen2 x1 / NVMe read-only mount, file checksum and unmount testing. The user also reported 10/10 cold boots and 10/10 reboots passing for this new image. Other peripheral and long-duration stress tests remain pending. Existing clean OpenWrt and hardware records remain historical evidence for their exact images.

## Advanced: build OpenWrt only on Linux / WSL2

Requirements: Git, Python 3, Docker, internet access and sufficient Linux build space. Do not build native OpenWrt in a Windows shell. Prefer a WSL ext4 work directory.

```sh
python3 tools/prepare.py
# For a different Linux build path: python3 tools/prepare.py --work /home/USER/work/myir-openwrt
# Adjust subsequent work path accordingly.
docker build -t myir/openwrt-build:noble -f tools/Dockerfile .
docker run --rm -v "$PWD/.work/openwrt:/work" -v "$PWD/tools:/setup:ro" -w /work myir/openwrt-build:noble bash -lc './scripts/feeds update -a && bash /setup/build-poc8.sh'
```

The builder runs as uid/gid 1000. Ensure your build directory is writable by that uid. The preparation script downloads the pinned vendor firmware and calibration files and verifies their SHA256; no firmware payload is stored in this repository. Consult the vendor firmware licensing before redistribution.

The exported first-boot script deliberately excludes the deployed root password/hash. A rebuilt image uses upstream initial password behavior: set a new root password through a trusted local console before network use. Existing board images/passwords are not changed by this export. Wi-Fi starts disabled; no personal SSID/key is included.

## Advanced: compose with a supplied legacy boot image

Provide the separately held `imx-boot-mys8mmx-v2-2025.04-poc1a.bin` in a private bootloader directory. Expected SHA256: `42c8e8c4b256fdc819b5b20c88569e40b69f8db72ff5c6bf92e4c31790e524c0`. This optional legacy mode accepts only that tested prebuilt hash. The complete workflow above instead downloads/builds the pinned boot sources and verifies the generated artifact using its build provenance. Proprietary binaries remain excluded from Git.

```sh
mkdir -p output
# Set BOOTLOADER_DIR to an absolute directory containing the file above.
docker run --rm -v "$PWD/.work/openwrt:/work:ro" -v "$PWD/tools:/setup:ro" -v "$PWD/output:/output" -v "$BOOTLOADER_DIR:/bootloader:ro" myir/openwrt-build:noble python3 /setup/compose-poc8.py
docker run --rm -v "$PWD/tools:/setup:ro" -v "$PWD/output:/output:ro" myir/openwrt-build:noble python3 /setup/verify-poc8.py
```

The compose script checks the boot blob hash, repairs bitmap padding on the exported rootfs copy, requires a clean EXT4 check, checks FAT and gzip roundtrip, and builds the complete SD image. Never flash an unverified output. Back up card contents and enable writer readback verification.

Some original diagnostic/unit/emulation scripts in `tools/` retain local `/home/myir` or `/mnt/d` paths and a private initial-access fixture. They are preserved as engineering references, not portable CI. Do not upload that fixture. No firmware image or secret is included in Git.

## Provenance and licensing

OpenWrt sources remain at https://github.com/openwrt/openwrt . Vendor board references are MYiR-Dev/myir-imx-linux commit `d1275dfcc8d52e51b720d42d95ee54853449970b` and the firmware commit recorded in the overlay JSON. Existing upstream/vendor notices and per-file licenses apply; this project does not grant a new license to vendor PDFs, firmware, DDR blobs or other third-party material. No board manuals or schematic PDFs are redistributed here.
