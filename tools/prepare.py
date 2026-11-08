#!/usr/bin/env python3
"""Prepare pinned upstream + MYIR port. Run on Linux/WSL, never in a populated build directory."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,urllib.request
repo=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--work',type=Path,default=repo/'.work/openwrt');args=a.parse_args()
w=args.work.resolve()
if w.exists():raise SystemExit('Destination exists; choose a new --work directory')
meta=json.loads((repo/'configs/source.json').read_text())
w.mkdir(parents=True)
def run(*cmd):subprocess.run(cmd,cwd=w,check=True)
run('git','init');run('git','remote','add','origin',meta['upstream'])
run('git','fetch','--depth=1','origin',meta['commit']);run('git','checkout','--detach','FETCH_HEAD')
run('git','apply','--check',str(repo/'patches/myir.patch'));run('git','apply',str(repo/'patches/myir.patch'))
shutil.copytree(repo/'overlay',w/'files',dirs_exist_ok=True)
for p in (w/'files').rglob('*'):
 if p.is_file() and ('sbin' in p.parts or 'uci-defaults' in p.parts):p.chmod(0o755)
for src,dst in [('myir-diffconfig','.config'),('myir-diffconfig','myir-diffconfig'),('feeds.conf','feeds.conf'),('feeds-pinned.txt','feeds-pinned.txt')]:shutil.copyfile(repo/'configs'/src,w/dst)
provenance=json.loads((w/'files/usr/share/myir/ap6256-firmware-provenance.json').read_text())
for item in provenance['files']:
 url='https://raw.githubusercontent.com/MYiR-Dev/myir-firmware/'+provenance['commit']+'/'+item['vendor_path']
 with urllib.request.urlopen(url,timeout=120) as response:data=response.read()
 if hashlib.sha256(data).hexdigest()!=item['sha256']:raise SystemExit('Firmware checksum mismatch: '+item['installed_name'])
 p=w/'files/lib/firmware/brcm'/item['installed_name'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
print('Prepared',meta['candidate'],'in',w)
print('No deployed password/hash was exported. Set a root password locally before network use.')
