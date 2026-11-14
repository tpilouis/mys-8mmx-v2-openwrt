# Build SPL, U-Boot, TF-A and a Complete SD Image from Source

Updated: 2026-11-14. Applies to the MYS-8MMX-V2, PCB V10, POC8.

[繁體中文](BOOTLOADER-FROM-SOURCE.zh-TW.md)

This workflow downloads the required components, compiles the open-source components and obtains proprietary NXP DDR training firmware. The proprietary firmware is not supplied as open source.

Integration and offline checks have passed locally. The rebuilt boot image reaches the OpenWrt shell. PCIe Gen2 x1 / NVMe read tests, 10 cold boots, 10 reboots and basic peripheral regression tests have passed. Long-duration stress testing remains pending. Results from the earlier clean image using an externally supplied POC1a boot file do not automatically apply to this rebuilt image.

## 1. Prepare the host PC

Complete sections 1–5 of the [beginner clean-build guide (Traditional Chinese)](BEGINNER-CLEAN-BUILD.zh-TW.md): Ubuntu 24.04 amd64 / WSL2, Git, Python 3, a separate Docker installation, a user with UID 1000 and a clone of this repository. Except where explicitly marked otherwise, run commands in the **Ubuntu terminal at the repository root**, not on the target board or in PowerShell.

## 2. Read the firmware license first

Read the [NXP firmware notice](../bootloader/NXP-FIRMWARE-NOTICE.md) and the applicable agreement. The DDR `.bin` files are proprietary; you must accept the applicable terms yourself before downloading and using them. If you do not accept, do not run commands with the acceptance option.

The archive is downloaded from NXP's official URL. Its version, archive SHA256, COPYING/SCR hashes and the hashes of the four DDR firmware files are pinned in [sources.json](../bootloader/sources.json). The script does not execute NXP's self-extracting installer or skip integrity checks. It refuses to download or extract firmware without the acceptance option.

For an archive you have already lawfully obtained, display its exact license and software content register without extracting firmware:

```bash
python3 tools/prepare-bootloader.py --show-license \
  --firmware-archive /absolute/path/firmware-imx-8.7.bin
```

## 3. Complete workflow for beginners

After reading and accepting the applicable terms, run:

```bash
bash tools/build-sd.sh --accept-nxp-eula
```

The workflow:

1. Builds the Docker build image.
2. Prepares the pinned OpenWrt source and feeds, then builds the toolchain, Linux, packages and root filesystem.
3. Downloads firmware-imx-8.7 from NXP, verifies it and extracts only the four DDR training firmware files and license documents.
4. Downloads pinned U-Boot, TF-A and imx-mkimage sources from NXP's GitHub repositories, verifying that each release tag resolves to its pinned commit.
5. Applies the MYIR board patch and verifies that the original vendor DDR timing is unchanged.
6. Builds SPL, U-Boot and TF-A using the GCC 14.3.0 toolchain produced by this OpenWrt build.
7. Packages the boot image with imx-mkimage and checks the ROM header, SPL, FIT, BL31 and embedded DDR payloads.
8. Validates the boot image against its build report, composes the SD image and checks filesystems, partitions, rootfs files and gzip round-trip integrity.

**No old POC1a boot file or full Yocto installation is required. The workflow does not automatically flash SD, eMMC or NOR storage.**

If this project's OpenWrt build has already completed successfully and you only need to rebuild the boot components and compose the image, use:

```bash
bash tools/build-sd.sh --accept-nxp-eula --skip-openwrt
```

Do not use `--skip-openwrt` for your first build from scratch. It does not create a missing toolchain; the workflow stops if required artifacts are absent.

### 3.1 Open the environment on the current Windows PC

Run in **PowerShell**. This example uses the WSL distribution and repository directory already created on the maintainer's PC:

```powershell
wsl -d MYIR-Clean -u myir --cd /home/myir/work/mys-8mmx-v2-openwrt
```

Then check inside **Ubuntu**:

```bash
pwd
id -u
docker info
ls tools/build-sd.sh bootloader/sources.json
```

`id -u` should return `1000`, and Docker must be accessible. On another PC, substitute your own WSL distribution name and clone directory. If a script is missing, check that your checkout includes this bootloader workflow. Use a repository revision containing tools/build-sd.sh; older revisions do not include this workflow.

For a first build, use the complete command in section 3. The existing MYIR-Clean environment, where OpenWrt has already been built, can use `--skip-openwrt`. This still prepares and builds the boot components, recomposes the SD image and runs checks; it does not merely copy an old boot file.

### 3.2 Build only SPL, U-Boot and TF-A (advanced)

Beginners should use the integrated entry point in section 3. The commands below are useful for debugging or rebuilding only the boot components. **They require a successful build in `.work/openwrt` and its generated cross toolchain.** Run them at the repository root in Ubuntu:

```bash
# Build the container image containing the build and verification tools.
docker build -t myir/openwrt-build:noble -f tools/Dockerfile .

# After accepting the NXP terms, fetch pinned sources, verify firmware and apply the board patch.
python3 tools/prepare-bootloader.py --accept-nxp-eula

mkdir -p output/bootloader
set -o pipefail
docker run --rm \
  -v "$PWD/.work/bootloader:/port" \
  -v "$PWD/.work/openwrt/staging_dir:/staging:ro" \
  -v "$PWD/tools:/setup:ro" \
  -v "$PWD/bootloader:/boot-config:ro" \
  -v "$PWD/output/bootloader:/output" \
  myir/openwrt-build:noble bash /setup/build-bootloader.sh \
  2>&1 | tee output/bootloader-build.log
```

The script builds SPL/U-Boot with `mys8mmx_v2_ddr4_defconfig`, builds TF-A BL31 with `PLAT=imx8mm`, then uses imx-mkimage's `flash_ddr4_evk` target to package the original DDR4 timing, training firmware and boot components. It checks the required Hush and boot.scr settings; no manual defconfig changes are needed.

The packaged boot file is `output/bootloader/imx-boot-mys8mmx-v2-2025.04-poc1a.bin`. Files such as `u-boot.bin` and `u-boot-spl.bin` are individual components, not substitutes for the packaged imx-boot file or a complete flashable SD image. Building the boot file does not update a card already installed in the board.

To create the complete SD image afterward, run:

```bash
bash tools/build-sd.sh --accept-nxp-eula --skip-openwrt
```

This runs the boot component build again, reusing existing build outputs where applicable, then completes image composition and offline checks.

## 4. Outputs and success criteria

| Location | Contents |
|---|---|
| `.work/openwrt` | OpenWrt source and the locally built cross toolchain |
| `.work/bootloader` | Three boot component source trees, DDR firmware and build directories |
| `.work/downloads` | Verified original NXP download archive |
| `output/bootloader` | Packaged boot file, SPL/BL31/FIT, configuration and build provenance |
| `output/from-zero` | Complete SD `.img` / `.img.gz` and verification reports |
| `output/logs` | Timestamped Docker, make, composition and verification logs |

The integrated workflow must finish with:

```text
FROM-SOURCE SD BUILD AND OFFLINE CHECKS PASSED: output/from-zero
```

The SD image filename is `openwrt-25.12.6-mys-8mmx-v2-sd-nvme-poc8.img.gz`.

`output/bootloader/bootloader-build.json` records the sources, DDR hashes, boot file SHA256 and checks. The composer compares this report with the repository's pinned source policy; it rejects arbitrary boot binaries and inconsistent source claims. This is a local build-consistency check, not independent digital-signature certification.

A legacy manual composition mode remains available for the old externally supplied POC1a file. Without build provenance, it accepts only the previously specified legacy SHA256. The beginner workflow does not use that mode.

## 5. Pinned versions and build date

| Component | Commit |
|---|---|
| NXP U-Boot 2025.04 | `4ddbad60eff308a5b356fb9ab8734ac382ddd692` |
| NXP TF-A v2.12 | `a266ff458c2526a6474036a5c6648be6fdc54fe3` |
| NXP imx-mkimage | `be80fadd5e7988214149a2bc48daac1b0950d4c2` |

The common release tag is `lf-6.12.49-2.2.0`. If a tag no longer resolves to the pinned commit, preparation stops rather than selecting a newer version.

Board changes are stored in `bootloader/uboot-myir.patch`. This includes the original vendor GPL DDR timing with its copyright and license notices preserved. Timing SHA256:

```text
d93343afc0b74b553ba4b3f210c40a945edc43ea75dac8ebca0864e8712ab8cd
```

The workflow does not regenerate timing or bypass DDR training on cold boot.

The timestamp is fixed to the original POC1a `SOURCE_DATE_EPOCH=1793875200`. Consequently, newly rebuilt SPL/U-Boot and BL31 still display **Nov 05 2026 10:40:00 UTC**. This is not the time when you ran make. Use the current logs in `output/logs` for execution times and SHA256 to identify artifacts. Different toolchains and build metadata may produce a hash different from the old prebuilt boot file. The new workflow checks pinned sources, build reports and actual output hashes rather than requiring equality with that legacy file.

## 6. Failures and retries

- **Acceptance option missing:** preparation exits before downloading firmware. This is expected.
- **NXP download unavailable:** keep the error log; do not change versions or bypass SHA256. You may lawfully obtain the specified archive yourself and run `python3 tools/prepare-bootloader.py --accept-nxp-eula --firmware-archive /path/file`. The integrated workflow must subsequently use the same pinned archive/cache.
- **Interrupted download:** a `.part` file is not treated as complete. Rerunning downloads the incomplete archive again.
- **Archive hash mismatch:** stop and check the download source. Do not modify the manifest to accept an unexpected file.
- **Tag, commit or patch mismatch:** stop and preserve local changes. Investigate or use another work directory; do not force-reset or indiscriminately delete your work.
- **Compilation failure:** fix the cause and rerun. Reusing this environment's own build cache is different from importing the old MYIR-Dev cache.
- **New patch incompatible with an existing `.work/openwrt`:** the entry point stops. `git pull` does not automatically port an existing source worktree.
- **Old output still exists after a failure:** do not treat it as a successful output of the failed run. Check the final success message and that run's logs.

## 7. Protective tests for developers and maintainers

After building the boot artifacts locally, run:

```bash
MYIR_TEST_BOOTLOADER_DIR="$PWD/output/bootloader" \
  python3 -m unittest discover -s tests -v
```

Tests cover the explicit acceptance requirement and rejection of altered boot data, source commits or build policy. Artifact tests are skipped if no artifacts have been built and the environment variable is not set; skipped tests do not mean full validation passed. All six tests were actually executed and passed for the recorded build.

## 8. What was actually validated

- OpenWrt was previously downloaded and built in the separate MYIR-Clean environment starting without a toolchain or Docker build image. Results and the necessary configuration-order fix are documented in the clean-build guide.
- The boot component work directory and DDR download cache did not previously exist. The three Git repositories and official NXP archive were downloaded anew. No boot binary or source cache was imported from MYIR-Dev.
- New SPL/U-Boot/TF-A/imx-mkimage builds, DDR payload checks and boot image structure checks passed.
- Both integrated wrapper modes, including the default full mode and the mode that skips OpenWrt, passed, as did final SD offline checks. OpenWrt in the default run reused MYIR-Clean's own freshly created cache; the entire WSL environment was not reinstalled again for this integration run.
- The new boot file differs from the old POC1a file. The new image reached the OpenWrt shell and passed PCIe Gen2 x1 / NVMe reads, 10 cold boots, 10 reboots and basic peripheral regression. Long-duration stress remains pending. Previously tested images are retained.

## 9. Test the image on the board

Back up settings, use a separate SD card, verify the new image's SHA256 and enable the flashing tool's write-readback verification. Power off before changing cards. Capture the complete serial output and confirm SPL DDR calibration, U-Boot 2025.04, 2 GiB DRAM, boot.scr and Linux startup. Then test DHCP, USB and SSD operation. Do not start by writing eMMC, NOR or fuses.

## 10. Hardware results for the rebuilt boot chain

On 2026-11-14, the user confirmed the new boot file SHA256:

```text
53ad61e8ab66ec0740a8126f2fe466697a9d27a7c61d4522e3b2bf5539e5a1c0
```

This identifies the tested artifact. Another toolchain or environment is not guaranteed to produce the same hash; use that build's provenance and checks to validate it.

| Item | Results for this rebuilt boot chain |
|---|---|
| SPL / DDR | DDR4 2400 MT/s calibration completed; 2 GiB detected |
| TF-A / U-Boot / SD | Loaded boot.scr, Image and DTB; started Linux 6.12.113 |
| Root filesystem | EXT4 mounted; OpenWrt 25.12.6 shell reached |
| PCIe / NVMe | With SSD inserted, Gen2 x1 (5.0 GT/s) link established; nvme0n1 and p1/p2 detected |
| SSD read-only | FAT mount, full kernel8.img SHA256 and unmount passed; hash matched earlier reads |
| Ethernet | 100Mbps full duplex; subsequent LuCI screenshot confirmed LAN DHCP client and 192.168.50.138/24 |
| USB | USB-A and Type-C Host FAT32 read-only mount/read/unmount passed; hashes of the same file matched |
| Wi-Fi | 2.4GHz channel 6 HT20 AP authentication/association and phone LuCI access passed; phone DHCP lease details were not supplied |
| RTC | RX8025T write exit=0, reads and five-second ticking passed; no battery, retention untested |
| SSH / LuCI | SSH password login and HTTPS LuCI overview, Interfaces and Wireless pages passed |
| Repeated boots | User reported 10/10 cold boots and 10/10 reboots, all passing |
| Long-duration stress | Untested; whether an earlier individual restart was manual remains unknown, separately from these 20 reported successful tests |

Run the SSD read-only test in the **board's serial or SSH shell**, after checking the device and partition. The tested SSD was a TS256GMTE400S with an existing FAT partition at p1:

```sh
mkdir -p /mnt/nvme
mount -t vfat -o ro /dev/nvme0n1p1 /mnt/nvme
sha256sum /mnt/nvme/kernel8.img
umount /mnt/nvme
```

The tested file's SHA256 was:

```text
55ea30cbb9fba29fd9fe8438a5324c715904116450c6f7169219c4d2b92d9dca
```

This value belongs to an existing file on that SSD. Other SSDs need not contain it. Matching earlier reads confirms consistency, not write performance or endurance. With no SSD inserted, failure to establish a PCIe link alone does not establish a porting defect.

A freshly built image has no preset root password. Set one using `passwd` on a trusted serial console before network use. The user did set a password for the recorded SSH/LuCI tests; no password or password hash is retained in these records.

See the [machine-readable validation record](../validation/bootloader-from-source-20261114.json) and [hardware status](HARDWARE-STATUS.md). Results are based on user-supplied output and screenshots. Storage writes/performance, 5GHz/client Wi-Fi, RTC battery retention and long-duration stress are outside this round's PASS results.
