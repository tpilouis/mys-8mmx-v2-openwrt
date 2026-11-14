#!/bin/bash
set -euo pipefail
jobs=${MYIR_JOBS:-8}
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'MYIR_JOBS must be a positive integer'; exit 2; }
export CROSS_COMPILE=/staging/toolchain-aarch64_cortex-a53_gcc-14.3.0_musl/bin/aarch64-openwrt-linux-musl-
export STAGING_DIR=/staging/target-aarch64_cortex-a53_musl
export SOURCE_DATE_EPOCH=$(python3 -c 'import json;print(json.load(open("/boot-config/sources.json"))["source_date_epoch"])')
export MYIR_CANDIDATE=poc1a
[ -x "${CROSS_COMPILE}gcc" ] || { echo 'Build OpenWrt first: its pinned cross compiler is required'; exit 1; }
cd /port/u-boot
make O=/port/build/u-boot mys8mmx_v2_ddr4_defconfig
for flag in CONFIG_TARGET_MYS8MMX_V2 CONFIG_ENV_IS_NOWHERE CONFIG_HUSH_PARSER CONFIG_HUSH_OLD_PARSER CONFIG_CMD_SOURCE CONFIG_LEGACY_IMAGE_FORMAT; do
    grep -q "^$flag=y$" /port/build/u-boot/.config
done
make O=/port/build/u-boot -j"$jobs" u-boot.bin spl/u-boot-spl.bin
make O=/port/build/u-boot -j"$jobs" tools-only
make -C /port/imx-atf BUILD_BASE=/port/build/atf PLAT=imx8mm -j"$jobs" bl31
cd /port/imx-mkimage/iMX8M
cp /port/build/u-boot/spl/u-boot-spl.bin .
cp /port/build/u-boot/u-boot-nodtb.bin .
cp /port/build/u-boot/arch/arm/dts/mys8mmx-v2.dtb .
cp /port/build/u-boot/tools/mkimage mkimage_uboot
cp /port/build/atf/imx8mm/release/bl31.bin .
for name in ddr4_imem_1d.bin ddr4_dmem_1d.bin ddr4_imem_2d.bin ddr4_dmem_2d.bin; do cp "/port/firmware/$name" .; done
cd ..
rm -f iMX8M/mkimage_imx8
make SOC=iMX8MM dtb_ddr4_evk=mys8mmx-v2.dtb TEE= flash_ddr4_evk
cp iMX8M/flash.bin /output/imx-boot-mys8mmx-v2-2025.04-poc1a.bin
cp iMX8M/u-boot-ddr4-evk.itb /output/u-boot-mys8mmx-v2.itb
cp /port/build/u-boot/arch/arm/dts/mys8mmx-v2.dtb /output/u-boot-mys8mmx-v2.dtb
cp /port/build/u-boot/spl/u-boot-spl.bin /output/u-boot-spl.bin
cp /port/build/u-boot/u-boot.bin /output/u-boot.bin
cp /port/build/atf/imx8mm/release/bl31.bin /output/bl31.bin
cp /port/build/u-boot/.config /output/uboot.config
cp /port/port-provenance.json /output/port-provenance.json
python3 /setup/verify-bootloader.py
printf '\nBOOTLOADER BUILD AND VERIFICATION PASSED\n'