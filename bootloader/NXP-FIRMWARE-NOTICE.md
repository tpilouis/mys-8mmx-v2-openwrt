# NXP DDR firmware notice

The source-only MYIR U-Boot patch, DDR timing C file and downloaded U-Boot/TF-A/imx-mkimage sources are distinct from the proprietary DDR training binaries.

The pinned archive is firmware-imx-8.7.bin, obtained from the NXP URL in sources.json. Its COPYING identifies LA_OPT_NXP_Software_License v11 February 2020. SCR.txt identifies proprietary DDR content from Synopsys and states that Production Use, Section 2.3 applies. This is not an open-source license or an unrestricted redistribution grant.

Review the applicable agreement and content register before downloading/using the firmware. Reference text for that version:
https://raw.githubusercontent.com/Freescale/meta-freescale/dunfell/EULA

Official archive:
https://www.nxp.com/lgfiles/NMG/MAD/YOCTO/firmware-imx-8.7.bin

Neither cloning this repo nor running a help command accepts the license. The preparation/build entry points refuse to download/extract firmware without the caller's explicit --accept-nxp-eula. For an archive you have lawfully obtained yourself, inspect the exact bundled text without executing the vendor installer:

    python3 tools/prepare-bootloader.py --show-license --firmware-archive /absolute/path/firmware-imx-8.7.bin

If you do not accept the applicable agreement, do not pass the acceptance option or use this firmware. Script acceptance is a caller declaration, not a new permission granted by this project.

Only sources, notices, hashes and download/build instructions belong in Git. Firmware archives, the four DDR .bin files and built boot/SD images are ignored and must stay outside repository history. Publishing a complete image is redistribution of its included components and requires a separate license/notice review; this workflow does not establish permission to publish images.

The vendor DDR timing C file included by the patch retains its original NXP copyright and GPL-2.0+ notice. Its exact SHA256 is pinned. The workflow does not regenerate timing or bypass cold-boot DDR training. Upstream sources retain their own license files; GNU GPLv2 text for the U-Boot-derived patch is in LICENSES/GPL-2.0.txt. TF-A is primarily BSD-3-Clause with per-file exceptions; imx-mkimage is GPLv2. No proprietary payloads or NXP manuals are included here.