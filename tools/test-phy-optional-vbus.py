from pathlib import Path
import subprocess
w=Path('/home/myir/work/openwrt-mys8mmx-v2-poc6')
p=next((w/'build_dir').glob('target-*/linux-imx_cortexa53/linux-6.12.113/drivers/usb/phy/phy-generic.c'))
s=p.read_text();start=s.index('\tif (device_property_present(dev, "vbus-supply"))');end=s.index('\n\tnop->dev',start);snippet=s[start:end]
pre=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <errno.h>
#define EPROBE_DEFER 517
#define PTR_ERR(p) ((long)(intptr_t)(p))
#define ERR_PTR(n) ((struct regulator *)(intptr_t)(n))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
struct regulator {int id;};
struct device {bool supply;};
struct usb_phy_generic {struct regulator *vbus_draw;};
static int requests;
static struct regulator *provider;
static bool device_property_present(struct device *d,const char *name){assert(strcmp(name,"vbus-supply")==0);return d->supply;}
static struct regulator *devm_regulator_get_exclusive(struct device *d,const char *name){(void)d;assert(strcmp(name,"vbus")==0);requests++;return provider;}
static int dev_err_probe(struct device *d,int err,const char *fmt,...){(void)d;(void)fmt;return err;}
static int probe(struct device *dev,struct usb_phy_generic *nop) {
'''
post=r'''
 return 0;
}
int main(void){
 struct device d={.supply=false};struct regulator r={1};struct usb_phy_generic n={0};
 provider=ERR_PTR(-EINVAL);requests=0;assert(probe(&d,&n)==0);assert(requests==0 && n.vbus_draw==NULL);
 d.supply=true;provider=&r;assert(probe(&d,&n)==0);assert(requests==1 && n.vbus_draw==&r);
 provider=ERR_PTR(-ENODEV);assert(probe(&d,&n)==0 && n.vbus_draw==NULL);
 provider=ERR_PTR(-EPROBE_DEFER);assert(probe(&d,&n)==-EPROBE_DEFER);
 provider=ERR_PTR(-EINVAL);assert(probe(&d,&n)==-EINVAL);
 puts("PASS: actual patched PHY VBUS lookup: absent supply skips exclusive dummy lookup; explicit supply retained; ENODEV optional; EPROBE_DEFER and real errors propagated. No physical VBUS emulated.");
 return 0;
}
'''
Path('/tmp/myir-phy-vbus-test.c').write_text(pre+snippet+post)
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','/tmp/myir-phy-vbus-test.c','-o','/tmp/myir-phy-vbus-test'],check=True)
r=subprocess.run(['/tmp/myir-phy-vbus-test'],check=True,text=True,capture_output=True)
Path('/mnt/d/MYIR-Dev/openwrt/logs/poc6/phy-optional-vbus-test.log').write_text(r.stdout)
print(r.stdout)