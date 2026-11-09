from pathlib import Path
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import urllib.error
import ssl
import hashlib

work=Path('/work')
logs=Path('/logs')
results={'hardware_test':False,'method':'ARM64 user-mode emulation; does not test kernel, PHY or SD hardware'}
archives=[p for p in (work/'bin/targets/imx/cortexa53').glob('*25.12.6*myir_mys-8mmx-v2*rootfs.tar.gz') if '-targz-' not in p.name]
if len(archives)!=1: raise RuntimeError('Expected MYIR rootfs tar.gz: '+str(archives))
scratch=Path(tempfile.mkdtemp(prefix='myir-rootfs-'))
with tarfile.open(archives[0]) as archive:
    # Rootfs is our freshly built artifact. Do not import external absolute paths.
    for member in archive.getmembers():
        if member.name.startswith('/') or '..' in Path(member.name).parts:
            raise RuntimeError('Unsafe rootfs member: '+member.name)
    members=archive.getmembers()
    absolute_links=[m for m in members if m.issym() and m.linkname.startswith('/')]
    archive.extractall(scratch,members=[m for m in members if not m.isdev() and m not in absolute_links],filter='tar')
    for member in absolute_links:
        link=scratch/member.name
        link.parent.mkdir(parents=True,exist_ok=True)
        link.symlink_to(member.linkname)
(scratch/'tmp').mkdir(exist_ok=True)
(scratch/'tmp/run').mkdir(parents=True,exist_ok=True)
(scratch/'tmp/run/ubus').mkdir(parents=True,exist_ok=True)
config=scratch/'etc/config/system'
if not config.exists(): config.write_text("config system\n\toption hostname 'OpenWrt'\n")
base=['proot','-0','-r',str(scratch),'-b','/dev','-b','/proc','-w','/','-q','/usr/bin/qemu-aarch64-static']
def call(*args,**kwargs):
    return subprocess.run(base+list(args),check=True,text=True,capture_output=True,timeout=60,**kwargs)
results['arm64_busybox']=call('/bin/busybox','uname','-m').stdout.strip()
call('/bin/sh','/etc/uci-defaults/99-myir-firstboot')
is_poc3=(scratch/'etc/myir-build').exists() and 'POC8' in (scratch/'etc/myir-build').read_text()
if is_poc3:
    # Synthetic UCI radio fixture tests defaults only; no RF device is emulated.
    (scratch/'etc/config/wireless').write_text("config wifi-device 'radio0'\n\toption type 'mac80211'\n\toption path 'test-only-fixture'\n\toption disabled '1'\nconfig wifi-iface 'default_radio0'\n\toption device 'radio0'\n\toption mode 'ap'\n\toption ssid 'OpenWrt'\n")
    call('/bin/sh','/etc/uci-defaults/zz-myir-wifi-client')
    assert call('/sbin/uci','get','network.lan.proto').stdout.strip()=='dhcp'
    assert call('/sbin/uci','get','network.wwan.proto').stdout.strip()=='dhcp'
    assert call('/sbin/uci','get','wireless.radio0.country').stdout.strip()=='TW'
    assert call('/sbin/uci','get','wireless.radio0.disabled').stdout.strip()=='1'
    assert 'default_radio0' not in call('/sbin/uci','show','wireless').stdout
    assert 'wwan' in call('/sbin/uci','show','firewall').stdout
    results['wifi_uci_defaults']='passed using synthetic UCI fixture; no radio hardware tested'
    firmware=json.loads((scratch/'usr/share/myir/ap6256-firmware-provenance.json').read_text())
    for entry in firmware['files']:
        assert hashlib.sha256((scratch/'lib/firmware/brcm'/entry['installed_name']).read_bytes()).hexdigest()==entry['sha256']
    assert list((scratch/'lib/modules').rglob('brcmfmac.ko'))
    assert (scratch/'www/luci-static/resources/view/network/wireless.js').exists()
    results['wifi_firmware_and_modules']='vendor SHA256, brcmfmac module and LuCI wireless view present'
    results['iw_version']=call('/usr/sbin/iw','--version').stdout.strip()
    results['wpa_supplicant_version']=call('/usr/sbin/wpa_supplicant','-v').stdout.strip()
else:
    assert call('/sbin/uci','get','network.lan.ipaddr').stdout.strip()=='192.168.77.1'
assert call('/sbin/uci','get','dhcp.lan.ignore').stdout.strip()=='1'
results['uci_initialization']='passed'
results['dropbear_version']=call('/usr/sbin/dropbear','-V').stderr.strip()
if (scratch/'etc/myir-build').exists():
    results['candidate']=(scratch/'etc/myir-build').read_text().strip()
    assert 'POC2' in results['candidate'] or 'POC8' in results['candidate']
    scripts=['/usr/sbin/myir-diag']
    scripts+=['/etc/uci-defaults/zz-myir-wifi-client','/usr/sbin/myir-wifi-diag'] if is_poc3 else ['/etc/hotplug.d/iface/99-myir-phy']
    for script in scripts:
        call('/bin/sh','-n',script)
    results['poc2_shell_syntax']='passed'
    results['ethtool_version']=call('/usr/sbin/ethtool','--version').stdout.strip()
    for name in ['myir-mdio-read','myir-diag','ethtool','i2cdetect']:
        assert (scratch/'usr/sbin'/name).exists() or (scratch/'usr/bin'/name).exists(), name
    results['poc2_diagnostic_tools']='present'
results['theme_preflight']=call('/usr/bin/ucode','-e',"import { access, stat } from 'fs'; let p='/usr/share/ucode/luci/template/themes/bootstrap/header.ut'; print(sprintf('access=%J stat=%J\\n',access(p),stat(p))); try { loadfile(p,{raw_mode:false}); print('template_compile_ok\\n'); } catch(e) { print(e.message); }").stdout
(logs/'userspace-preflight.json').write_text(json.dumps(results,indent=2))
password=Path('/private/INITIAL-ACCESS.txt').read_text().split('Password: ',1)[1].splitlines()[0]
secret=Path(tempfile.mkstemp(prefix='myir-ssh-secret-')[1])
secret.write_text(password+'\n'); secret.chmod(0o600)
services=[]
handles=[]
def start(name,args):
    handle=(logs/(name+'.log')).open('w')
    handles.append(handle)
    process=subprocess.Popen(base+args,stdout=handle,stderr=subprocess.STDOUT)
    services.append(process)
    return process
try:
    start('dropbear-smoke',['/usr/sbin/dropbear','-F','-E','-R','-p','127.0.0.1:22222','-P','/tmp/dropbear-smoke.pid'])
    time.sleep(2)
    ssh=subprocess.run(['sshpass','-f',str(secret),'ssh','-T','-p','22222','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','-o','ConnectTimeout=10','root@127.0.0.1','echo MYIR_SSH_OK'],text=True,capture_output=True,timeout=60,check=True)
    assert 'MYIR_SSH_OK' in ssh.stdout
    results['ssh_password_login']='passed under ARM64 userspace emulation'
    start('ubus-smoke',['/sbin/ubusd','-s','/var/run/ubus/ubus.sock'])
    for _ in range(50):
        if (scratch/'tmp/run/ubus/ubus.sock').exists(): break
        time.sleep(0.1)
    else: raise RuntimeError('ubusd socket did not appear')
    start('procd-smoke',['/sbin/procd','-S','-s','/var/run/ubus/ubus.sock'])
    time.sleep(2)
    start('rpcd-smoke',['/sbin/rpcd','-s','/var/run/ubus/ubus.sock'])
    time.sleep(1)
    login=json.loads(call('/bin/ubus','call','session','login',json.dumps({'username':'root','password':password})).stdout)
    assert login.get('ubus_rpc_session')
    results['luci_rpc_password_auth']='passed with real rpcd'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(scratch/'etc/uhttpd.key'),'-out',str(scratch/'etc/uhttpd.crt'),'-days','1','-subj','/CN=localhost'],check=True,capture_output=True)
    start('uhttpd-smoke',['/usr/sbin/uhttpd','-f','-h','/www','-p','127.0.0.1:18080','-s','127.0.0.1:18443','-C','/etc/uhttpd.crt','-K','/etc/uhttpd.key','-u','/ubus','-U','/var/run/ubus/ubus.sock'])
    time.sleep(2)
    for path in ['/','/cgi-bin/luci/']:
        try:
            request=urllib.request.urlopen('http://127.0.0.1:18080'+path,timeout=30)
        except urllib.error.HTTPError as error:
            body=error.read()
            if path!='/cgi-bin/luci/' or error.code!=403 or b'luci_password' not in body or b'bootstrap.sysauth' not in body:
                (logs/'luci-smoke-response.html').write_bytes(body)
                raise
            request=error
            results['luci_login_page']='passed; expected unauthenticated HTTP 403'
        else:
            body=request.read()
        if not body: raise RuntimeError('Empty web response: '+path)
        results['http_'+path]={'status':request.status,'bytes':len(body)}
        if path=='/cgi-bin/luci/':
            (logs/'luci-smoke-response.html').write_bytes(body)
    try:
        response=urllib.request.urlopen('https://127.0.0.1:18443/cgi-bin/luci/',context=ssl._create_unverified_context(),timeout=30)
    except urllib.error.HTTPError as response:
        assert response.code==403 and b'luci_password' in response.read()
    results['https_luci_login_page']='passed with test-only self-signed certificate'
    results['status']='passed'
finally:
    for process in services:
        if process.poll() is None: process.terminate()
    for process in services:
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill()
    for handle in handles: handle.close()
    secret.unlink(missing_ok=True)
    (logs/'userspace-smoke.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))


assert (scratch/'usr/sbin/myir-peripheral-diag').exists()
call('/bin/sh','-n','/usr/sbin/myir-peripheral-diag')
results['usbutils_version']=call('/usr/bin/lsusb','--version').stdout.strip()
assert (scratch/'sbin/block').exists()
assert (scratch/'lib/modules/6.12.113/rtc-rx8025t.ko').exists()
assert call('/sbin/uci','get','fstab.@global[0].anon_mount').stdout.strip()=='0'
results['rtc_usb_tools']='passed: RTC module, lsusb, block, shell syntax, anonymous automount disabled; no peripheral hardware emulated'
(logs/'userspace-smoke.json').write_text(json.dumps(results,indent=2))
print(results['rtc_usb_tools'])
call('/bin/sh','-n','/usr/sbin/myir-typec-diag')
results['typec_host_userspace']='passed: Type-C diagnostic shell syntax; physical USB1 Host/CC/VBUS require hardware tests'
(logs/'userspace-smoke.json').write_text(json.dumps(results,indent=2))
call('/bin/sh','-n','/usr/sbin/myir-m2-diag')
assert (scratch/'lib/modules/6.12.113/nvme.ko').exists()
assert (scratch/'lib/modules/6.12.113/nvme-core.ko').exists()
results['pciutils_version']=call('/usr/bin/lspci','--version').stdout.strip()
results['nvme_version']=call('/usr/sbin/nvme','version').stdout.strip()
results['m2_userspace']='passed: diagnostic syntax, NVMe modules and PCI/NVMe tools; hardware not emulated'
(logs/'userspace-smoke.json').write_text(json.dumps(results,indent=2))