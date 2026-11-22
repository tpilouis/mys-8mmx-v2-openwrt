# Source provenance and licensing

Original project code, scripts, configuration and documentation are GPL-2.0-only unless an existing file or upstream license specifies otherwise. See [LICENSE](LICENSE). The project is maintained by Louis Chou and is not an official MYIR, NXP or OpenWrt product.

| Material | Treatment |
|---|---|
| Original port-kit tooling and documentation | GPL-2.0-only, Copyright 2026 Louis Chou |
| Linux/OpenWrt patches and RX8025T driver | Existing upstream and per-file licenses apply; RTC driver is GPL-2.0-only and retains vendor/driver attribution |
| Device-tree files | Existing SPDX notices, including dual GPL-2.0-or-later / MIT where stated, are preserved |
| U-Boot board patch and original DDR timing | Existing GPL-2.0-or-later notices and NXP copyrights retained |
| Downloaded OpenWrt, U-Boot, TF-A and imx-mkimage | Retain upstream licenses; fixed source locations/commits are recorded in configs and bootloader manifests |
| NXP/Synopsys DDR training firmware | Proprietary; excluded from Git. Explicit acceptance and hash-verified download are required; see bootloader/NXP-FIRMWARE-NOTICE.md |
| AP6256 Wi-Fi firmware and calibration data | Downloaded separately from the pinned MYIR repository; not included in Git. Availability on GitHub is not a new redistribution license. Users must review applicable vendor terms |
| Vendor manuals/schematics and complete firmware images | Not distributed in this repository |

## Included diagnostic executable

`overlay/usr/sbin/myir-mdio-read` is a small project-built AArch64/musl ELF diagnostic, not a vendor firmware blob. The original corresponding source is now supplied as `tools/myir-mdio-read.c` under GPL-2.0-only. Its SHA256 is recorded in the public preparation report. It only issues Clause 22 PHY read ioctls.

After building this project's OpenWrt toolchain, rebuild it from the repository root in Ubuntu:

```sh
mkdir -p output/diagnostics
docker run --rm \
  -e STAGING_DIR=/staging/target-aarch64_cortex-a53_musl \
  -v "$PWD/.work/openwrt/staging_dir:/staging:ro" \
  -v "$PWD/tools:/setup:ro" \
  -v "$PWD/output/diagnostics:/output" \
  myir/openwrt-build:noble \
  /staging/toolchain-aarch64_cortex-a53_gcc-14.3.0_musl/bin/aarch64-openwrt-linux-musl-gcc \
  -O2 -g -Wall -Wextra /setup/myir-mdio-read.c -o /output/myir-mdio-read
```

Compiler flags, source paths and debug metadata can affect the binary hash; byte-for-byte reproduction of the historical executable is not claimed. The existing executable is retained to preserve the hardware-tested image baseline. No private access fixture is included; historical smoke scripts requiring `/private/INITIAL-ACCESS.txt` are engineering references, not the beginner build entry point.

Publishing source does not establish permission to redistribute complete firmware images containing proprietary components. Review those components' terms separately before distributing binaries.
