# Local artifacts

Original private development sources: WSL MYIR-Dev `/home/myir/work/openwrt-mys8mmx-v2-poc6` and `...-poc7`. These worktrees are unchanged by the Git export.

Windows project export: `D:\MYIR-Dev\repos\mys-8mmx-v2-openwrt`.

Built images and full validation outputs remain under `D:\MYIR-Dev\openwrt\output-poc6` and `output-poc7`; caches, images, binaries, private initial credentials and vendor PDF manuals are excluded from Git. The exported credential-free overlay differs intentionally from the original deployed image. Exported reports/checksums document historical originals, not a bit-identical rebuilt credential-free image.

Board boot blob is held separately at `D:\MYIR-Dev\uboot-port\output-poc1a`; original DDR timing and training binaries were not regenerated. U-Boot source is a separate local project and not silently included in this OpenWrt port kit.
