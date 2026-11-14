"""Safety checks; artifact cases use your locally built, untracked boot image."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
from bootloader_artifact import BOOT_NAME, validated_bootloader


class ConsentGate(unittest.TestCase):
    def test_prepare_requires_explicit_acceptance_before_creating_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'must-not-be-created'
            result = subprocess.run([sys.executable, str(REPO / 'tools/prepare-bootloader.py'),
                                     '--work', str(work)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('--accept-nxp-eula', result.stderr)
            self.assertFalse(work.exists())

    def test_wrapper_requires_acceptance_before_docker(self):
        result = subprocess.run(['bash', str(REPO / 'tools/build-sd.sh'), '--skip-openwrt'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--accept-nxp-eula', result.stderr)


@unittest.skipUnless(os.environ.get('MYIR_TEST_BOOTLOADER_DIR'),
                     'Set MYIR_TEST_BOOTLOADER_DIR after a successful local boot build')
class BuiltArtifact(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        source = Path(os.environ['MYIR_TEST_BOOTLOADER_DIR'])
        for name in [BOOT_NAME, 'bootloader-build.json']:
            shutil.copyfile(source / name, self.directory / name)
        self.policy = REPO / 'bootloader/sources.json'

    def test_accepts_verified_build(self):
        _, evidence = validated_bootloader(self.directory, self.policy)
        self.assertEqual(evidence['mode'], 'rebuilt_from_pinned_sources')

    def test_rejects_changed_boot_payload(self):
        path = self.directory / BOOT_NAME
        data = bytearray(path.read_bytes()); data[len(data) // 2] ^= 1
        path.write_bytes(data)
        with self.assertRaises(ValueError):
            validated_bootloader(self.directory, self.policy)

    def test_rejects_changed_source_commit(self):
        path = self.directory / 'bootloader-build.json'
        proof = json.loads(path.read_text())
        proof['sources']['u-boot']['commit'] = '0' * 40
        path.write_text(json.dumps(proof))
        with self.assertRaises(ValueError):
            validated_bootloader(self.directory, self.policy)

    def test_rejects_changed_build_policy(self):
        policy = json.loads(self.policy.read_text())
        policy['source_date_epoch'] += 1
        changed = self.directory / 'sources.json'
        changed.write_text(json.dumps(policy))
        shutil.copyfile(REPO / 'bootloader/uboot-myir.patch', self.directory / 'uboot-myir.patch')
        with self.assertRaises(ValueError):
            validated_bootloader(self.directory, changed)


if __name__ == '__main__':
    unittest.main()
