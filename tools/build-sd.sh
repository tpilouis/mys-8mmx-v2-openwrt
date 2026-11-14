#!/bin/bash
# Run on the Ubuntu/WSL host as uid 1000, not inside the target board.
set -euo pipefail
accept=0
skip_openwrt=0
for argument in "$@"; do
    case "$argument" in
        --accept-nxp-eula) accept=1 ;;
        --skip-openwrt) skip_openwrt=1 ;;
        -h|--help)
            echo 'Usage: bash tools/build-sd.sh --accept-nxp-eula [--skip-openwrt]'
            echo 'Build pinned OpenWrt, SPL/U-Boot, TF-A, imx-mkimage and a verified SD candidate.'
            echo 'Read bootloader/NXP-FIRMWARE-NOTICE.md before accepting.'
            echo 'Use --skip-openwrt only after a successful build in .work/openwrt.'
            exit 0 ;;
        *) echo "Unknown option: $argument" >&2; exit 2 ;;
    esac
done
if [ "$accept" != 1 ]; then
    echo 'NXP proprietary DDR firmware requires explicit --accept-nxp-eula; see bootloader/NXP-FIRMWARE-NOTICE.md.' >&2
    exit 2
fi
[ "$(id -u)" = 1000 ] || { echo 'This tested workflow expects host uid 1000; see the beginner guide.' >&2; exit 1; }
for command in git python3 docker; do command -v "$command" >/dev/null; done
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo"
docker info >/dev/null
mkdir -p output/logs output/bootloader output/from-zero
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker build --progress=plain -t myir/openwrt-build:noble -f tools/Dockerfile . 2>&1 | tee "output/logs/docker-$stamp.log"
if [ ! -d .work/openwrt ]; then
    [ "$skip_openwrt" = 0 ] || { echo 'No OpenWrt build exists to skip'; exit 1; }
    python3 tools/prepare.py
fi
expected=$(python3 -c 'import json; print(json.load(open("configs/source.json"))["commit"])')
[ "$(git -C .work/openwrt rev-parse HEAD)" = "$expected" ] || { echo 'OpenWrt commit differs from pinned policy'; exit 1; }
git -C .work/openwrt apply --reverse --check "$repo/patches/myir.patch"
if [ "$skip_openwrt" = 0 ]; then
    # Restore current tracked configuration/overlay after git pull as well.
    python3 - <<'PY'
from pathlib import Path
import hashlib,json,shutil
repo=Path.cwd();work=repo/'.work/openwrt'
for name in ['myir-diffconfig','feeds-pinned.txt','feeds.conf']:
    shutil.copyfile(repo/'configs'/name,work/name)
shutil.copytree(repo/'overlay',work/'files',dirs_exist_ok=True)
for path in (work/'files').rglob('*'):
    if path.is_file() and ('sbin' in path.parts or 'uci-defaults' in path.parts):path.chmod(0o755)
policy=json.loads((repo/'overlay/usr/share/myir/ap6256-firmware-provenance.json').read_text())
allowed={str(p.relative_to(repo/'overlay')) for p in (repo/'overlay').rglob('*') if p.is_file()}
for item in policy['files']:
    name='lib/firmware/brcm/'+item['installed_name'];allowed.add(name)
    if hashlib.sha256((work/'files'/name).read_bytes()).hexdigest()!=item['sha256']:
        raise SystemExit('Wi-Fi firmware differs from pinned policy: '+name)
unexpected={str(p.relative_to(work/'files')) for p in (work/'files').rglob('*') if p.is_file()}-allowed
if unexpected:raise SystemExit('Unexpected overlay files; preserve custom data and use a fresh work directory: '+str(sorted(unexpected)))
PY
    docker run --name "myir-fromzero-openwrt-$stamp" \
        -v "$repo/.work/openwrt":/work -v "$repo/tools":/setup:ro -w /work \
        myir/openwrt-build:noble bash -lc './scripts/feeds update -a && bash /setup/build-poc8.sh' \
        2>&1 | tee "output/logs/openwrt-$stamp.log"
fi
[ -x .work/openwrt/staging_dir/toolchain-aarch64_cortex-a53_gcc-14.3.0_musl/bin/aarch64-openwrt-linux-musl-gcc ] || {
    echo 'Expected OpenWrt cross compiler is missing'; exit 1;
}
python3 tools/prepare-bootloader.py --accept-nxp-eula 2>&1 | tee "output/logs/boot-prepare-$stamp.log"
docker run --name "myir-fromzero-boot-$stamp" \
    -v "$repo/.work/bootloader":/port -v "$repo/.work/openwrt/staging_dir":/staging:ro \
    -v "$repo/tools":/setup:ro -v "$repo/bootloader":/boot-config:ro \
    -v "$repo/output/bootloader":/output myir/openwrt-build:noble \
    bash /setup/build-bootloader.sh 2>&1 | tee "output/logs/boot-build-$stamp.log"
docker run --rm -v "$repo/.work/openwrt":/work:ro -v "$repo/tools":/setup:ro \
    -v "$repo/bootloader":/boot-config:ro -v "$repo/output/bootloader":/bootloader:ro \
    -v "$repo/output/from-zero":/output myir/openwrt-build:noble \
    python3 /setup/compose-poc8.py 2>&1 | tee "output/logs/compose-$stamp.log"
docker run --rm -v "$repo/tools":/setup:ro -v "$repo/output/from-zero":/output:ro \
    myir/openwrt-build:noble python3 /setup/verify-poc8.py \
    2>&1 | tee "output/logs/artifacts-$stamp.log"
docker run --rm -v "$repo/.work/openwrt":/work:ro -v "$repo/tools":/setup:ro \
    -v "$repo/output/from-zero":/output:ro myir/openwrt-build:noble \
    python3 /setup/verify-disk-poc8.py 2>&1 | tee "output/logs/disk-$stamp.log"
echo 'FROM-SOURCE SD BUILD AND OFFLINE CHECKS PASSED: output/from-zero'
echo 'Board testing remains required. No SD/eMMC/NOR writes were performed.'
