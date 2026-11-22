# Security policy

This is an experimental board bring-up project. Only the pinned POC8 source workflow and the hardware tests recorded in docs/HARDWARE-STATUS.md have been validated. There is no production support or guaranteed security-update schedule. HABv4 secure boot is not enabled in the current bootloader configuration; image hash checks are not a substitute for authenticated secure boot.

## Reporting a vulnerability

Use the repository's GitHub **Security → Report a vulnerability** feature for suspected security issues. Do not publish passwords, tokens, private keys or an exploitable vulnerability in a public issue. If private reporting is unavailable, contact the maintainer at tpilouis@gmail.com with a brief description and arrange a private exchange before sending sensitive material.

## Using rebuilt images

- Set a new root password through a trusted serial console before network use. No preset password or deployed password hash is included in this repository.
- Wi-Fi starts disabled. Configure your own SSID/key locally; do not commit credentials or diagnostic output containing them.
- Keep management interfaces on a trusted network. Review upstream security updates before production deployment.
- Do not program secure-boot eFuses as part of this workflow; it performs no fuse writes.

For ordinary build or hardware questions, use GitHub Issues and include the repository commit, build error and sanitized diagnostic output.
