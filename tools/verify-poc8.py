from pathlib import Path
import subprocess
import json

dtb='/output/imx8mm-mys-8mmx-v2.dtb'
def get(node,prop,kind='s'):
    return subprocess.check_output(['fdtget','-t',kind,dtb,node,prop],text=True).strip()
assert 'POC8 M.2 NVMe candidate' in get('/','model')
sdio='/soc@0/bus@30800000/mmc@30b40000'
assert get(sdio,'status')=='okay'
assert get(sdio,'max-frequency','u')=='50000000'
assert get(sdio,'bus-width','u')=='4'
for flag in ['non-removable','no-1-8-v','cap-sdio-irq']:
    subprocess.run(['fdtget',dtb,sdio,flag],check=True,capture_output=True)
assert get(sdio+'/wifi@1','brcm,board-type')=='myir,mys-8mmx-v2'
assert get('/wifi-pwrseq','reset-gpios','u').split()[-2:]==['10','1']
assert get('/regulator-wifi','gpio','u').split()[-2:]==['15','0']
assert get('/regulator-wifi-parent','gpio','u').split()[-2:]==['11','0']
assert get('/regulator-wifi','vin-supply','u')==get('/regulator-wifi-parent','phandle','u')
assert get(sdio,'vmmc-supply','u')==get('/regulator-wifi','phandle','u')
assert get(sdio,'mmc-pwrseq','u')==get('/wifi-pwrseq','phandle','u')
phy='/soc@0/bus@30800000/ethernet@30be0000/mdio/ethernet-phy@4'
assert get(phy,'reset-gpios','u').split()[-2:]==['22','0']
assert get('/soc@0/bus@30800000/crypto@30900000','status')=='disabled'
assert get('/soc@0/bus@30800000/i2c@30a20000','clock-frequency','u')=='100000'
root='/output/rootfs.ext4'
def cat(path):
    return subprocess.check_output(['debugfs','-R','cat '+path,root],text=True,stderr=subprocess.DEVNULL)
assert 'POC8' in cat('/etc/myir-build')
assert "option proto 'dhcp'" in cat('/etc/config/network')
assert 'wwan' in cat('/etc/uci-defaults/zz-myir-wifi-client')
firmware=json.loads(cat('/usr/share/myir/ap6256-firmware-provenance.json'))
assert firmware['commit']=='6406ae805c805230528bd121ee8e7419face4810'
module=subprocess.check_output(['debugfs','-R','cat /lib/modules/6.12.113/brcmfmac.ko',root],stderr=subprocess.DEVNULL)
assert b'__sdio_register_driver' in module and b'brcmfmac43456-sdio' in module
print('POC8 compiled DTB: Wi-Fi parent/power/reset chain, SDIO, Ethernet reset and PMIC settings verified.')
print('Exported rootfs marker, DHCP client defaults and firmware provenance verified.')
print('Exported brcmfmac module contains SDIO registration and BCM43456 firmware mapping.')

rtc='/soc@0/bus@30800000/i2c@30a30000/rtc@32'
assert get('/aliases','rtc0')==rtc
assert get(rtc,'compatible')=='epson,rx8025t'
assert get(rtc,'reg','u')=='50'
assert get('/soc@0/bus@30800000/i2c@30a30000','status')=='okay'
usb='/soc@0/bus@32c00000/usb@32e50000'
assert get(usb,'status')=='okay'
assert get(usb,'dr_mode')=='host'
subprocess.run(['fdtget',dtb,usb,'disable-over-current'],check=True,capture_output=True)
assert get('/usbphynop1','status')=='okay'
assert get('/usbphynop2','vbus-supply','u')==get('/regulator-usb-host-vbus','phandle','u')
assert get('/regulator-usb-host-vbus','regulator-min-microvolt','u')=='5000000'
assert 'read-only' in cat('/usr/sbin/myir-peripheral-diag')
assert "option anon_mount '0'" in cat('/etc/config/fstab')
module=subprocess.check_output(['debugfs','-R','cat /lib/modules/6.12.113/rtc-rx8025t.ko',root],stderr=subprocess.DEVNULL)
# Upstream rx8025 uses I2C ID matching, not an OF match table; boot autoload is explicit.
assert b'rx8025t' in module
print('POC8 RTC I2C address/alias/module and USB2 Host fixed VBUS verified; Type-C PHY enabled.')
config=Path('/output/kernel-build.config').read_text()
for flag in ['CONFIG_RTC_CLASS=y','# CONFIG_RTC_DRV_RX8025 is not set','CONFIG_USB_CHIPIDEA_IMX=y','CONFIG_USB_CHIPIDEA_HOST=y']:
    assert flag in config,flag
for flag in ['CONFIG_USB_STORAGE','CONFIG_EXFAT_FS','CONFIG_VFAT_FS','CONFIG_EXT4_FS']:
    assert flag+'=y' in config or flag+'=m' in config,flag
assert 'rtc-rx8025t' in cat('/etc/modules.d/50-rtc-rx8025t')
link=subprocess.check_output(['debugfs','-R','stat /etc/modules-boot.d/50-rtc-rx8025t',root],text=True,stderr=subprocess.DEVNULL)
assert '../modules.d/50-rtc-rx8025t' in link
print('RX8025 boot autoload and compiled RTC/USB/filesystem kernel options verified.')
assert not cat('/etc/modules.d/50-rtc-rx8025').strip()
print('Generic SA/NB driver removed; dedicated RX8025T module and OF compatible verified.')

usb1='/soc@0/bus@32c00000/usb@32e40000'
assert get(usb1,'status')=='okay'
assert get(usb1,'dr_mode')=='host'
assert subprocess.run(['fdtget',dtb,'/usbphynop1','vbus-supply'],capture_output=True).returncode!=0
assert 'read-only' in cat('/usr/sbin/myir-typec-diag')
assert 'i2cset' not in cat('/usr/sbin/myir-typec-diag')
print('POC8 USB1 Type-C fixed Host and USB2 Host verified; no invented Type-C VBUS supply/control GPIO.')
pcie='/soc@0/pcie@33800000'
phy='/soc@0/bus@32c00000/pcie-phy@32f00000'
assert get(pcie,'status')=='okay'
assert get(pcie,'num-lanes','u')=='1'
assert get(pcie,'fsl,max-link-speed','u')=='2'
assert get(pcie,'reset-gpio','u').split()[-2:]==['21','1']
assert get(pcie,'vpcie-supply','u')==get('/regulator-wifi-parent','phandle','u')
assert get(phy,'status')=='okay'
assert get(phy,'fsl,refclk-pad-mode','u')=='2'
assert 'CONFIG_BLK_DEV_NVME=m' in config
assert 'CONFIG_PHY_FSL_IMX8M_PCIE=y' in config
assert 'read-only' in cat('/usr/sbin/myir-m2-diag')
assert cat('/etc/modules.d/30-nvme').strip()
print('POC8 PCIe x1 Gen2, CPU clock output, reset/supply and NVMe autoload verified.')
# Compare compiled trees semantically after accounting for the intended changes.
reference='/baseline/imx8mm-mys-8mmx-v2.dtb'
if Path(reference).exists():
    previous=subprocess.check_output(['dtc','-I','dtb','-O','dts',reference],text=True,stderr=subprocess.DEVNULL)
    current=subprocess.check_output(['dtc','-I','dtb','-O','dts',dtb],text=True,stderr=subprocess.DEVNULL)
    normalized=current.replace('POC8','POC7').replace('fsl,max-link-speed = <0x02>;','fsl,max-link-speed = <0x01>;',1)
    assert normalized==previous,'Unexpected DTB differences beyond model and Gen2 speed'
    print('POC7/POC8 compiled DTB comparison PASS: only model label and PCIe speed differ.')