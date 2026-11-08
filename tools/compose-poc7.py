from pathlib import Path
import gzip
import hashlib
import json
import os
import shutil
import struct
import subprocess

work = Path('/work')
out = Path('/output')
out.mkdir(parents=True, exist_ok=True)
bin_dir = work / 'bin/targets/imx/cortexa53'
prefix = 'openwrt-25.12.6-imx-cortexa53-myir_mys-8mmx-v2'

def run(*args):
    subprocess.run([str(a) for a in args], check=True)

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            value.update(block)
    return value.hexdigest()

kernel = bin_dir / (prefix + '-kernel.bin')
rootfs_gz = bin_dir / (prefix + '-ext4-rootfs.img.gz')
if not rootfs_gz.is_file():
    options = list(bin_dir.glob('*myir_mys-8mmx-v2*rootfs.img.gz'))
    if len(options) != 1: raise RuntimeError('Cannot uniquely identify ext4 rootfs: ' + str(options))
    rootfs_gz = options[0]
dtbs = list((work / 'build_dir').glob('target-*/linux-imx_cortexa53/image-imx8mm-mys-8mmx-v2.dtb'))
if len(dtbs) != 1: raise RuntimeError('Cannot uniquely identify MYIR DTB: ' + str(dtbs))
dtb = dtbs[0]
dtb_name = 'imx8mm-mys-8mmx-v2.dtb'
if kernel.read_bytes()[56:60] != b'ARMd': raise RuntimeError('Invalid ARM64 kernel header')
if dtb.read_bytes()[:4] != b'\xd0\x0d\xfe\xed': raise RuntimeError('Invalid device tree header')
boot = Path('/bootloader/imx-boot-mys8mmx-v2-2025.04-poc1a.bin')
expected_boot = '42c8e8c4b256fdc819b5b20c88569e40b69f8db72ff5c6bf92e4c31790e524c0'
if digest(boot) != expected_boot: raise RuntimeError('POC1a boot chain checksum mismatch')

shutil.copyfile(kernel, out / 'Image')
shutil.copyfile(dtb, out / dtb_name)
shutil.copyfile(boot, out / 'imx-boot-poc1a')
shutil.copyfile('/setup/boot-openwrt-poc7.cmd', out / 'boot-openwrt.cmd')
run('mkimage','-A','arm64','-O','linux','-T','script','-C','none','-n','MYIR OpenWrt SD wired','-d','/setup/boot-openwrt-poc7.cmd',out/'boot.scr')

sector = 512
boot_start = 8 * 1024**2
boot_size = 64 * 1024**2
root_start = boot_start + boot_size
root_size = 512 * 1024**2
image = out / 'openwrt-25.12.6-mys-8mmx-v2-sd-nvme-poc7.img'
rootfs = out / 'rootfs.ext4'
with gzip.open(rootfs_gz, 'rb') as source, rootfs.open('wb') as target:
    shutil.copyfileobj(source, target)
if rootfs.stat().st_size > root_size: raise RuntimeError('Root filesystem exceeds partition size')
with rootfs.open('rb') as stream:
    stream.seek(1024 + 56)
    if stream.read(2) != b'\x53\xef': raise RuntimeError('Missing ext4 superblock')
# Normalize make_ext4fs bitmap padding on our export copy, then require a clean
# read-only verification. Original OpenWrt build artifacts remain unchanged.
preen = subprocess.run(['e2fsck','-pf',str(rootfs)])
if preen.returncode not in (0,1): raise RuntimeError('Root filesystem preen failed')
run('e2fsck','-fn',rootfs)

fat = out / 'boot-fat.img'
with fat.open('wb') as stream: stream.truncate(boot_size)
run('mkfs.fat','-F','32','-n','OPENWRTBOOT',fat)
for name in ['Image',dtb_name,'boot.scr']:
    run('mcopy','-i',fat,out/name,'::'+name)
run('fsck.fat','-n',fat)

mbr = bytearray(512)
struct.pack_into('<I',mbr,440,0x4d595232)
def partition(index, active, kind, start, size):
    struct.pack_into('<B3sB3sII',mbr,446 + index*16,active,b'\xfe\xff\xff',kind,b'\xfe\xff\xff',start//sector,size//sector)
partition(0,0x80,0x0c,boot_start,boot_size)
partition(1,0,0x83,root_start,root_size)
mbr[510:512] = b'\x55\xaa'
with image.open('wb') as stream:
    stream.truncate(root_start + root_size)
    stream.seek(0); stream.write(mbr)
    stream.seek(33*1024); stream.write(boot.read_bytes())
    for offset, source in [(boot_start,fat),(root_start,rootfs)]:
        stream.seek(offset)
        with source.open('rb') as data: shutil.copyfileobj(data,stream)
run('fdisk','-l',image)
with image.open('rb') as stream:
    if stream.read(512) != mbr: raise RuntimeError('MBR readback failed')
    stream.seek(33*1024)
    if hashlib.sha256(stream.read(boot.stat().st_size)).hexdigest() != expected_boot:
        raise RuntimeError('Boot chain readback failed')
    stream.seek(root_start + 1024 + 56)
    if stream.read(2) != b'\x53\xef': raise RuntimeError('Root partition offset check failed')
compressed = image.with_suffix('.img.gz')
with image.open('rb') as source, compressed.open('wb') as target:
    with gzip.GzipFile(filename='',mode='wb',fileobj=target,mtime=0,compresslevel=6) as stream:
        shutil.copyfileobj(source,stream)
with gzip.open(compressed,'rb') as stream:
    decoded = hashlib.sha256()
    for block in iter(lambda:stream.read(4*1024**2),b''): decoded.update(block)
if decoded.hexdigest() != digest(image): raise RuntimeError('Compressed image readback failed')

for source in bin_dir.glob('openwrt-25.12.6-*myir_mys-8mmx-v2*initramfs*'):
    shutil.copyfile(source,out/source.name)
for source in bin_dir.glob('openwrt-25.12.6-*.manifest'):
    if 'myir_mys-8mmx-v2' in source.name: shutil.copyfile(source,out/source.name)
shutil.copyfile(work/'.config',out/'openwrt-build.config')
shutil.copyfile(work/'myir-diffconfig',out/'myir-diffconfig')
shutil.copyfile(work/'feeds-pinned.txt',out/'feeds-pinned.txt')
report = {'status':'build_candidate_hardware_test_pending','base_release':'25.12.6','candidate':'POC7 M.2 NVMe candidate','bootloader':'2025.04 MYIR POC1a unchanged','source_commit':subprocess.check_output(['git','-C',str(work),'rev-parse','HEAD'],text=True).strip(),'disk_signature':'4d595232','boot_offset_bytes':33*1024,'boot_partition_offset_bytes':boot_start,'root_partition_offset_bytes':root_start,'root_partuuid':'4d595232-02','management_ip':'DHCP client; see router lease or serial console','dhcp_server':False,'hardware_test':False,'files':[]}
for path in sorted(out.iterdir()):
    if path.is_file() and path.name not in ['SHA256SUMS.txt','build-report.json']:
        report['files'].append({'name':path.name,'bytes':path.stat().st_size,'sha256':digest(path)})
(out/'SHA256SUMS.txt').write_text(''.join(row['sha256']+'  '+row['name']+'\n' for row in report['files']))
(out/'build-report.json').write_text(json.dumps(report,indent=2))
print('SD CANDIDATE CREATED AND STATICALLY VERIFIED:',compressed.name)


configs=list((work/'build_dir').glob('target-*/linux-imx_cortexa53/linux-6.12.113/.config'))
assert len(configs)==1
shutil.copyfile(configs[0],out/'kernel-build.config')
