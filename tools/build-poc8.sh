#!/bin/bash
set -euo pipefail
if [ "${MYIR_RUN_SNAPSHOT:-}" != 1 ]; then
  snapshot_path=$(mktemp /tmp/myir-poc8-build.XXXXXX)
  cp -- "$0" "$snapshot_path"
  MYIR_RUN_SNAPSHOT=1 exec bash "$snapshot_path"
fi
cd /work
if ! ./scripts/feeds install -a; then echo "Optional feed dependency warnings; checking selected configuration."; fi
# Unselected legacy LuCI WeeChat metadata forms a Kconfig dependency cycle.
[ ! -L package/feeds/luci/luci-app-weechat ] || unlink package/feeds/luci/luci-app-weechat
make defconfig
grep -q '^CONFIG_TARGET_imx_cortexa53_DEVICE_myir_mys-8mmx-v2=y' .config
grep -q '^CONFIG_PACKAGE_luci-ssl=y' .config
grep -q '^CONFIG_PACKAGE_kmod-brcmfmac=y' .config
 grep -q '^CONFIG_PACKAGE_kmod-rtc-rx8025t=y' .config
 grep -q '^CONFIG_PACKAGE_block-mount=y' .config
./scripts/diffconfig.sh > myir-diffconfig
printf '=== POC8: downloading maintenance sources ===\n'
make download -j8 V=s
printf '=== POC8: RTC/USB kernel and firmware build ===\n'
make -j8 V=s
printf '=== POC8 BUILD SUCCEEDED ===\n'