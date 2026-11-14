"""Validate a rebuilt boot artifact against this project's pinned source policy."""
from pathlib import Path
import hashlib
import json

BOOT_NAME = 'imx-boot-mys8mmx-v2-2025.04-poc1a.bin'
LEGACY_SHA256 = '42c8e8c4b256fdc819b5b20c88569e40b69f8db72ff5c6bf92e4c31790e524c0'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validated_bootloader(directory, manifest_path=Path('/boot-config/sources.json')):
    directory = Path(directory)
    boot = directory / BOOT_NAME
    digest = sha(boot)
    proof_path = directory / 'bootloader-build.json'
    if not proof_path.exists():
        if digest != LEGACY_SHA256:
            raise ValueError('Unknown prebuilt boot blob: rebuild it using tools/build-sd.sh')
        return boot, {'mode': 'legacy_prebuilt', 'sha256': digest,
                      'note': 'Previously tested externally supplied POC1a artifact'}
    policy = json.loads(Path(manifest_path).read_text())
    proof = json.loads(proof_path.read_text())
    checks = [
        proof.get('schema') == 1,
        proof.get('status') == 'verified_from_pinned_sources',
        proof.get('manifest_sha256') == sha(Path(manifest_path)),
        proof.get('patch_sha256') == policy['patch_sha256'],
        sha(Path(manifest_path).parent / 'uboot-myir.patch') == policy['patch_sha256'],
        proof.get('sources') == policy['sources'],
        proof.get('board') == policy['board'],
        proof.get('source_date_epoch') == policy['source_date_epoch'],
        proof.get('ddr_timing_sha256') == policy['ddr_timing']['sha256'],
        proof.get('firmware_archive_sha256') == policy['firmware']['sha256'],
        proof.get('training_firmware') == policy['firmware']['files'],
        proof.get('offline_verification', {}).get('offline_checks') == 'passed',
        proof.get('boot_image', {}).get('name') == BOOT_NAME,
        proof.get('boot_image', {}).get('sha256') == digest,
        proof.get('boot_image', {}).get('bytes') == boot.stat().st_size,
    ]
    if not all(checks):
        raise ValueError('Rebuilt boot provenance or output checksum does not match pinned policy')
    return boot, {'mode': 'rebuilt_from_pinned_sources', 'sha256': digest, 'build': proof}
