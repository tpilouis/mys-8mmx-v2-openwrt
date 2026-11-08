from pathlib import Path
import subprocess
src=Path('/mnt/d/MYIR-Dev/openwrt/setup/rtc-rx8025t.c').read_text()
core=src[src.index('#define RX8025T_SEC'):src.index('static const struct rtc_class_ops')]
pre=r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) (((~0U) >> (31-(h))) & ((~0U) << (l)))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
static unsigned int __ffs(unsigned int v) {return __builtin_ctz(v);}
static int bcd2bin(unsigned int v) {return (v>>4)*10+(v&15);}
static u8 bin2bcd(unsigned int v) {return ((v/10)<<4)|(v%10);}
struct device {int unused;};
struct i2c_client {struct device dev;};
#define to_i2c_client(d) ((struct i2c_client *)(d))
struct rtc_time {int tm_sec,tm_min,tm_hour,tm_wday,tm_mday,tm_mon,tm_year;};
static int rtc_valid_tm(struct rtc_time *t) {
 static const int days[]={31,28,31,30,31,30,31,31,30,31,30,31};
 int y=t->tm_year+1900,d;
 if(t->tm_mon<0||t->tm_mon>11||t->tm_sec<0||t->tm_sec>59||t->tm_min<0||t->tm_min>59||t->tm_hour<0||t->tm_hour>23)return -EINVAL;
 d=days[t->tm_mon]+(t->tm_mon==1 && y%4==0 && (y%100!=0||y%400==0));
 return t->tm_mday<1||t->tm_mday>d ? -EINVAL:0;
}
static u8 registers[16];
static int fail_read,short_read,fail_block_write;
static int i2c_smbus_read_byte_data(struct i2c_client *c,u8 reg) {
 (void)c;assert(reg<16);if(fail_read)return -EIO;return registers[reg];
}
static int i2c_smbus_write_byte_data(struct i2c_client *c,u8 reg,u8 val) {
 (void)c;assert(reg<16);
 if(reg==0x0e) registers[reg]&=val; /* Device flags are write-zero-to-clear. */
 else registers[reg]=val;
 return 0;
}
static int i2c_smbus_read_i2c_block_data(struct i2c_client *c,u8 reg,int n,u8 *buf) {
 (void)c;assert(reg==0 && n==7);if(fail_read)return -EIO;
 memcpy(buf,registers,n);return short_read?3:n;
}
static int i2c_smbus_write_i2c_block_data(struct i2c_client *c,u8 reg,int n,const u8 *buf) {
 (void)c;assert(reg==0 && n==7);if(fail_block_write)return -EIO;
 memcpy(registers,buf,n);return 0;
}
'''
post=r'''
int main(void) {
 struct i2c_client c={0};struct rtc_time in={.tm_sec=56,.tm_min=34,.tm_hour=12,.tm_wday=6,.tm_mday=7,.tm_mon=10,.tm_year=126},out={0};
 memset(registers,0,sizeof(registers));registers[14]=0x3b;registers[13]=0xff;
 assert(rx8025t_init_client(&c)==0);assert(registers[14]==3);assert(registers[13]==0);assert(registers[15]==0x40);
 assert(rx8025t_read_time(&c.dev,&out)==-EINVAL);
 registers[14]|=8;
 assert(rx8025t_set_time(&c.dev,&in)==0);
 assert(registers[0]==0x56 && registers[1]==0x34 && registers[2]==0x12);
 assert(registers[3]==0x40 && registers[4]==0x07 && registers[5]==0x11 && registers[6]==0x26);
 assert(registers[14]==8 && registers[15]==0x40);
 assert(rx8025t_read_time(&c.dev,&out)==0);
 assert(out.tm_sec==56 && out.tm_min==34 && out.tm_hour==12 && out.tm_wday==6 && out.tm_year==126 && out.tm_mon==10 && out.tm_mday==7);
 for(int i=0;i<7;i++){in.tm_wday=i;assert(rx8025t_set_time(&c.dev,&in)==0);assert(registers[3]==BIT(i));assert(rx8025t_read_time(&c.dev,&out)==0);assert(out.tm_wday==i);}
 registers[0]=0x57;assert(rx8025t_read_time(&c.dev,&out)==0 && out.tm_sec==57);
 fail_read=1;assert(rx8025t_read_time(&c.dev,&out)==-EIO);assert(rx8025t_set_time(&c.dev,&in)==-EIO);fail_read=0;
 short_read=1;assert(rx8025t_read_time(&c.dev,&out)==-EIO);short_read=0;
 fail_block_write=1;assert(rx8025t_set_time(&c.dev,&in)==-EIO);assert(registers[15]&1);assert(rx8025t_init_client(&c)==0);assert(registers[15]&1);assert(rx8025t_read_time(&c.dev,&out)==-EINVAL);fail_block_write=0;
 assert(rx8025t_set_time(&c.dev,&in)==0);assert(!(registers[15]&1));
 in.tm_year=99;assert(rx8025t_set_time(&c.dev,&in)==-EINVAL);in.tm_year=200;assert(rx8025t_set_time(&c.dev,&in)==-EINVAL);
 in.tm_year=199;in.tm_mon=11;in.tm_mday=31;assert(rx8025t_set_time(&c.dev,&in)==0);assert(rx8025t_read_time(&c.dev,&out)==0 && out.tm_year==199);
 in.tm_year=100;in.tm_mon=1;in.tm_mday=29;assert(rx8025t_set_time(&c.dev,&in)==0);
 in.tm_year=101;assert(rx8025t_set_time(&c.dev,&in)==-EINVAL);
 registers[3]=3;assert(rx8025t_read_time(&c.dev,&out)==-EINVAL);registers[3]=1;registers[0]=0x1a;assert(rx8025t_read_time(&c.dev,&out)==-EINVAL);
 assert(rx8025t_set_time(&c.dev,&in)==-EINVAL);
 puts("PASS: actual RX8025T core with simulated I2C: direct addressing, invalid-state retention, write/read, seven weekdays, counter read, I/O errors, partial-write/reset recovery, year range, leap date and invalid BCD.");
 return 0;
}
'''
p=Path('/tmp/myir-rx8025t-test.c');p.write_text(pre+core+post)
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-O2',str(p),'-o','/tmp/myir-rx8025t-test'],check=True)
r=subprocess.run(['/tmp/myir-rx8025t-test'],check=True,text=True,capture_output=True)
Path('/mnt/d/MYIR-Dev/openwrt/logs/poc5a/rtc-protocol-test.log').write_text(r.stdout)
print(r.stdout)