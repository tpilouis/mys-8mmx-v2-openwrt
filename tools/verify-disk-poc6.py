from pathlib import Path
import hashlib,struct,subprocess,tempfile,gzip,json,tarfile
out=Path('/output'); image=out/'openwrt-25.12.6-mys-8mmx-v2-sd-typec-host-poc6.img'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
with tempfile.TemporaryDirectory() as td:
 with image.open('rb') as f:
  mbr=f.read(512);assert mbr[510:]==b'\x55\xaa'
  assert struct.unpack_from('<I',mbr,440)[0]==0x4d595232
  for i,name,checker in [(0,'boot-fat.img',['fsck.fat','-n']),(1,'rootfs.ext4',['e2fsck','-fn'])]:
   start,size=struct.unpack_from('<II',mbr,446+16*i+8)
   assert start*512==[8,72][i]*1024**2
   p=Path(td)/name
   f.seek(start*512)
   with p.open('wb') as dest:
    remain=size*512
    while remain:
     b=f.read(min(remain,4*1024**2));assert b;dest.write(b);remain-=len(b)
   ref=Path('/intermediate')/name
   if not ref.exists():ref=out/name
   assert sha(p)==sha(ref),name+' partition differs from checked source'
   subprocess.run(checker+[str(p)],check=True)
   if i==1:
    extracted=Path(td)/'extracted';extracted.mkdir()
    subprocess.run(['debugfs','-R','rdump / '+str(extracted),str(p)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    archive=next(Path('/work/bin/targets/imx/cortexa53').glob('*v2-rootfs.tar.gz'))
    count=0
    with tarfile.open(archive) as tar:
     for m in tar:
      if m.isfile():
       dest=extracted/m.name
       assert dest.is_file(),m.name
       assert sha(dest)==hashlib.file_digest(tar.extractfile(m),'sha256').hexdigest(),m.name
       count+=1
    print('All rootfs regular files match ARM64 smoke-test archive:',count,flush=True)
   print(name,'full partition readback and filesystem check PASS',flush=True)
 with gzip.open(str(image)+'.gz','rb') as f:
  assert hashlib.file_digest(f,'sha256').hexdigest()==sha(image)
 for row in (out/'SHA256SUMS.txt').read_text().splitlines():
  digest,name=row.split('  ',1);assert sha(out/name)==digest,name
print('ALL final-image partitions, gzip roundtrip, and SHA256SUMS PASS')