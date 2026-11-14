from pathlib import Path
import hashlib
import json
import struct
import subprocess
import os
from boot_source_state import verify_source_trees

root=Path('/port')
out=Path('/output')
provenance=json.loads((out/'port-provenance.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
timing=root/'u-boot/board/myir/mys8mmx_v2/ddr4_timing.c'
assert sha(timing)==provenance['ddr_timing_sha256']
candidate=os.environ.get('MYIR_CANDIDATE','poc1a')
raw=(out/('imx-boot-mys8mmx-v2-2025.04-'+candidate+'.bin')).read_bytes()
assert raw[0]==0xd1 and raw[3]==0x41
assert struct.unpack_from('<I',raw,4)[0]==0x7e1000
spl=(out/'u-boot-spl.bin').read_bytes()
assert raw[0x40:0x40+len(spl)]==spl
fit=(out/'u-boot-mys8mmx-v2.itb').read_bytes()
packed_fit=bytearray(raw[0x57c00:0x57c00+len(fit)])
# NXP mkimage adds two 32-byte HAB IVTs in reserved FIT padding. All actual
# FDT metadata and external image data must remain identical to the FIT input.
for offset in [0x1000,0x3000]:
    assert fit[offset:offset+32]==bytes(32)
    assert packed_fit[offset]==0xd1 and packed_fit[offset+3]==0x40
    packed_fit[offset:offset+32]=bytes(32)
assert packed_fit==fit
offsets={}
for item in provenance['training_firmware']:
    p=root/'firmware'/item['name']
    assert sha(p)==item['sha256']
    offset=raw.find(p.read_bytes())
    assert offset>=0
    offsets[item['name']]=offset
def get(file,node,prop,kind='s'):
    return subprocess.check_output(['fdtget','-t',kind,str(file),node,prop],text=True).strip()
dtb=out/'u-boot-mys8mmx-v2.dtb'
assert 'MYIR MYS-8MMX-V2' in get(dtb,'/','model')
assert get(dtb,'/aliases','mmc1').endswith('mmc@30b50000')
assert get(dtb,'/chosen','stdout-path').endswith('serial@30890000')
assert get(out/'u-boot-mys8mmx-v2.itb','/images/atf-1','entry','x')=='920000'
config=(out/'uboot.config').read_text()
for flag in ['CONFIG_ENV_IS_NOWHERE=y','CONFIG_IMX8M_DDR4=y','CONFIG_TARGET_MYS8MMX_V2=y']:
    assert flag in config
if candidate=='poc1a':
    for flag in ['CONFIG_HUSH_PARSER=y','CONFIG_HUSH_OLD_PARSER=y','CONFIG_LEGACY_IMAGE_FORMAT=y','CONFIG_CMD_SOURCE=y']:
        assert flag in config
    assert b'parse_string_outer' in (root/'build/u-boot/u-boot').read_bytes()
assert '# CONFIG_ENV_IS_IN_MMC is not set' in config
assert 'scriptaddr=0x40480000' in (root/'build/u-boot/include/generated/env.in').read_text()
for p in [root/'build/u-boot/u-boot',root/'build/u-boot/spl/u-boot-spl',root/'build/atf/imx8mm/release/bl31/bl31.elf']:
    header=p.read_bytes()[:20]
    assert header[:4]==b'\x7fELF' and struct.unpack_from('<H',header,18)[0]==183
report={'offline_checks':'passed','hardware_test':False,'ddr_timing_unchanged':True,'training_firmware_unchanged':True,'firmware_offsets_in_boot_image':offsets,'boot_image_bytes':len(raw),'spl_bytes':len(spl),'fit_offset_in_boot_image':0x57c00,'fit_offset_on_sd':0x60000,'environment':'volatile; MMC environment writes disabled','pending':['cold boot','DDR training','U-Boot prompt','SD reads','Linux handoff','reboots and DDR stress testing']}
(out/'verification-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

# Verify pinned inputs again against the actual compiled checkout.
policy_path=Path('/boot-config/sources.json')
policy=json.loads(policy_path.read_text())
assert sha(policy_path)==provenance['manifest_sha256']
assert sha(Path('/boot-config/uboot-myir.patch'))==policy['patch_sha256']==provenance['patch_sha256']
for name,source in policy['sources'].items():
    assert subprocess.check_output(['git','-C',str(root/name),'rev-parse','HEAD'],text=True).strip()==source['commit']
source_trees=verify_source_trees(root,policy,Path('/boot-config/uboot-myir.patch'))
subprocess.run(['git','-C',str(root/'u-boot'),'apply','--reverse','--check','/boot-config/uboot-myir.patch'],check=True)
assert sha(timing)==policy['ddr_timing']['sha256']
for item in policy['firmware']['files']:
    assert sha(root/'firmware'/item['name'])==item['sha256']
assert sha(root/'firmware/COPYING')==policy['firmware']['license_sha256']
assert sha(root/'firmware/SCR.txt')==policy['firmware']['content_register_sha256']
boot_name='imx-boot-mys8mmx-v2-2025.04-poc1a.bin'
proof={'schema':1,'status':'verified_from_pinned_sources','board':policy['board'],
       'manifest_sha256':sha(policy_path),'patch_sha256':policy['patch_sha256'],
       'sources':policy['sources'],'source_date_epoch':policy['source_date_epoch'],
       'verified_source_trees':source_trees,
       'ddr_timing_sha256':sha(timing),'firmware_archive_sha256':policy['firmware']['sha256'],
       'training_firmware':policy['firmware']['files'],
       'license_acceptance':provenance['license_acceptance'],
       'boot_image':{'name':boot_name,'bytes':(out/boot_name).stat().st_size,'sha256':sha(out/boot_name)},
       'matches_previous_tested_poc1a':sha(out/boot_name)=='42c8e8c4b256fdc819b5b20c88569e40b69f8db72ff5c6bf92e4c31790e524c0',
       'hardware_test':False,'offline_verification':report}
(out/'bootloader-build.json').write_text(json.dumps(proof,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
print('Boot source, DDR, embedded payload and image provenance checks PASS')
