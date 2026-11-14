#!/usr/bin/env python3
"""Fetch pinned boot sources and verified DDR blobs; never execute the NXP installer."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import urllib.request


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def firmware_members(archive, policy):
    if sha(archive) != policy['sha256']:
        raise SystemExit('NXP archive SHA256 mismatch; do not bypass verification')
    data = archive.read_bytes()
    offset = data.find(b'BZh')
    if offset < 0:
        raise SystemExit('Expected firmware-imx bzip2 payload was not found')
    with tarfile.open(fileobj=io.BytesIO(data[offset:]), mode='r:bz2') as tar:
        result = {}
        wanted = {'COPYING': policy['license_sha256'],
                  'SCR.txt': policy['content_register_sha256']}
        wanted.update({item['name']: item['sha256'] for item in policy['files']})
        for name, digest in wanted.items():
            matches = [m for m in tar.getmembers() if m.name.endswith('/' + name)]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 2_000_000:
                raise SystemExit('Invalid or ambiguous archive member: ' + name)
            value = tar.extractfile(matches[0]).read()
            if hashlib.sha256(value).hexdigest() != digest:
                raise SystemExit('Archive member SHA256 mismatch: ' + name)
            result[name] = value
        return result


def main():
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=repo / '.work/bootloader')
    parser.add_argument('--firmware-archive', type=Path)
    parser.add_argument('--accept-nxp-eula', action='store_true',
                        help='Confirm you have read and accept the pinned NXP firmware license')
    parser.add_argument('--show-license', action='store_true',
                        help='Print COPYING/SCR from --firmware-archive, without extracting binaries')
    args = parser.parse_args()
    manifest_path = repo / 'bootloader/sources.json'
    policy = json.loads(manifest_path.read_text())
    fw = policy['firmware']
    if args.show_license:
        if not args.firmware_archive:
            parser.error('--show-license requires an already downloaded --firmware-archive')
        members = firmware_members(args.firmware_archive, fw)
        print(members['COPYING'].decode())
        print(members['SCR.txt'].decode())
        return
    # Gate before creating a work directory, downloading or extracting software.
    if not args.accept_nxp_eula:
        parser.error('DDR firmware is proprietary. Review ' + fw['license'] + '\n' +
                     fw['license_reference_url'] + '\nThen explicitly pass --accept-nxp-eula. '
                     'No license acceptance is inferred from cloning this repository.')
    patch = repo / 'bootloader/uboot-myir.patch'
    if sha(patch) != policy['patch_sha256']:
        raise SystemExit('Board patch differs from the pinned manifest')
    archive = args.firmware_archive
    if archive is None:
        cache = repo / '.work/downloads'
        cache.mkdir(parents=True, exist_ok=True)
        archive = cache / fw['filename']
        if not archive.exists():
            temporary = archive.with_suffix(archive.suffix + '.part')
            print('Downloading official NXP archive:', fw['url'], flush=True)
            with urllib.request.urlopen(fw['url'], timeout=120) as source, temporary.open('wb') as target:
                while block := source.read(1024 * 1024):
                    target.write(block)
            if sha(temporary) != fw['sha256']:
                raise SystemExit('Downloaded NXP archive SHA256 mismatch')
            temporary.replace(archive)
    members = firmware_members(archive, fw)
    # A manually obtained archive must also support the normal wrapper later,
    # including when the official server is unavailable during that later run.
    if args.firmware_archive is not None:
        cache = repo / '.work/downloads'
        cache.mkdir(parents=True, exist_ok=True)
        cached = cache / fw['filename']
        if cached.exists() and sha(cached) != fw['sha256']:
            raise SystemExit('Existing cached NXP archive has the wrong SHA256; inspect it first')
        if not cached.exists():
            shutil.copyfile(archive, cached)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    for name, source in policy['sources'].items():
        directory = work / name
        if not directory.exists():
            directory.mkdir()
            subprocess.run(['git', 'init', str(directory)], check=True)
            subprocess.run(['git', '-C', str(directory), 'remote', 'add', 'origin', source['url']], check=True)
        def git(*command):
            return subprocess.check_output(['git', '-C', str(directory), *command], text=True,
                                           stderr=subprocess.PIPE).strip()
        try:
            head = git('rev-parse', 'HEAD')
        except subprocess.CalledProcessError:
            tag = policy['release_tag']
            subprocess.run(['git', '-C', str(directory), 'fetch', '--depth=1', 'origin',
                            'refs/tags/' + tag + ':refs/tags/' + tag], check=True)
            head = git('rev-parse', tag + '^{commit}')
            if head != source['commit']:
                raise SystemExit('Release tag no longer matches pinned commit: ' + name)
            subprocess.run(['git', '-C', str(directory), 'checkout', '--detach', source['commit']], check=True)
        if head != source['commit']:
            raise SystemExit('Unexpected existing checkout: ' + name)
        if name == 'u-boot':
            reverse = subprocess.run(['git', '-C', str(directory), 'apply', '--reverse', '--check',
                                      str(patch)], capture_output=True)
            if reverse.returncode:
                subprocess.run(['git', '-C', str(directory), 'apply', '--check', '--whitespace=nowarn', str(patch)], check=True)
                subprocess.run(['git', '-C', str(directory), 'apply', '--whitespace=nowarn', str(patch)], check=True)
    timing = work / 'u-boot' / policy['ddr_timing']['path']
    if sha(timing) != policy['ddr_timing']['sha256']:
        raise SystemExit('Original DDR timing changed')
    firmware = work / 'firmware'
    firmware.mkdir(exist_ok=True)
    for name, value in members.items():
        (firmware / name).write_bytes(value)
    provenance = {
        'vendor_uboot_commit': policy['ddr_timing']['vendor_commit'],
        'ddr_timing_sha256': policy['ddr_timing']['sha256'],
        'ddr_timing_unchanged': True, 'training_firmware': fw['files'],
        'hardware_test': False, 'nxp_release_tag': policy['release_tag'],
        'u-boot_commit': policy['sources']['u-boot']['commit'],
        'imx-atf_commit': policy['sources']['imx-atf']['commit'],
        'imx-mkimage_commit': policy['sources']['imx-mkimage']['commit'],
        'manifest_sha256': sha(manifest_path), 'patch_sha256': sha(patch),
        'nxp_firmware_archive_sha256': fw['sha256'],
        'license_acceptance': 'Explicit --accept-nxp-eula supplied by caller',
        'license_sha256': fw['license_sha256'],
    }
    (work / 'port-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('Pinned boot sources and DDR firmware prepared:', work)


if __name__ == '__main__':
    main()
