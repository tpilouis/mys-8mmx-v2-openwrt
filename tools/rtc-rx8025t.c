// SPDX-License-Identifier: GPL-2.0-only
/*
 * Epson RX-8025T basic RTC support for MYIR MYS-8MMX-V2.
 * Register protocol based on MYIR rtc-rx8025t.c (Kevin Su), itself derived
 * from the RX8025 driver by Wolfgang Grandegger / Digi International.
 * Linux 6.12 adaptation: managed RTC allocation, validity handling,
 * one-hot weekday encoding and explicit reset during time writes.
 * RX-8025T uses direct register addresses, unlike RX-8025 SA/NB.
 */
#include <linux/bcd.h>
#include <linux/bitops.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/rtc.h>

#define RX8025T_SEC 0x00
#define RX8025T_EXT 0x0d
#define RX8025T_FLAG 0x0e
#define RX8025T_CTRL 0x0f
#define RX8025T_VDET BIT(0)
#define RX8025T_VLF BIT(1)
#define RX8025T_RESET BIT(0)
#define RX8025T_CSEL GENMASK(7, 6)
#define RX8025T_CSEL_2S BIT(6)

static int rx8025t_read_reg(struct i2c_client *client, u8 reg)
{
	return i2c_smbus_read_byte_data(client, reg);
}

static int rx8025t_read_time(struct device *dev, struct rtc_time *tm)
{
	struct i2c_client *client = to_i2c_client(dev);
	u8 data[7], weekday;
	int flags, ctrl, ret, i;

	flags = rx8025t_read_reg(client, RX8025T_FLAG);
	if (flags < 0)
		return flags;
	ctrl = rx8025t_read_reg(client, RX8025T_CTRL);
	if (ctrl < 0)
		return ctrl;
	if ((flags & (RX8025T_VLF | RX8025T_VDET)) || (ctrl & RX8025T_RESET))
		return -EINVAL;

	ret = i2c_smbus_read_i2c_block_data(client, RX8025T_SEC, sizeof(data), data);
	if (ret != (int)sizeof(data))
		return ret < 0 ? ret : -EIO;

	data[0] &= 0x7f;
	data[1] &= 0x7f;
	data[2] &= 0x3f;
	data[4] &= 0x3f;
	data[5] &= 0x1f;
	for (i = 0; i < (int)ARRAY_SIZE(data); i++) {
		if (i == 3)
			continue;
		if ((data[i] & 0xf) > 9 || (data[i] >> 4) > 9)
			return -EINVAL;
	}
	weekday = data[3] & 0x7f;
	if (!weekday || (weekday & (weekday - 1)))
		return -EINVAL;

	tm->tm_sec = bcd2bin(data[0]);
	tm->tm_min = bcd2bin(data[1]);
	tm->tm_hour = bcd2bin(data[2]);
	tm->tm_wday = __ffs(weekday);
	tm->tm_mday = bcd2bin(data[4]);
	tm->tm_mon = bcd2bin(data[5]) - 1;
	tm->tm_year = bcd2bin(data[6]) + 100;
	return rtc_valid_tm(tm);
}

static int rx8025t_set_time(struct device *dev, struct rtc_time *tm)
{
	struct i2c_client *client = to_i2c_client(dev);
	u8 data[7];
	int ctrl, flags, ret;

	ret = rtc_valid_tm(tm);
	if (ret)
		return ret;
	if (tm->tm_year < 100 || tm->tm_year > 199 || tm->tm_wday < 0 || tm->tm_wday > 6)
		return -EINVAL;

	ctrl = rx8025t_read_reg(client, RX8025T_CTRL);
	if (ctrl < 0)
		return ctrl;
	ctrl &= RX8025T_CSEL; /* No IRQ line is connected on this board. */
	ret = i2c_smbus_write_byte_data(client, RX8025T_CTRL, ctrl | RX8025T_RESET);
	if (ret < 0)
		return ret;

	data[0] = bin2bcd(tm->tm_sec);
	data[1] = bin2bcd(tm->tm_min);
	data[2] = bin2bcd(tm->tm_hour);
	data[3] = BIT(tm->tm_wday); /* Binary one-hot; never BCD-convert. */
	data[4] = bin2bcd(tm->tm_mday);
	data[5] = bin2bcd(tm->tm_mon + 1);
	data[6] = bin2bcd(tm->tm_year - 100);
	ret = i2c_smbus_write_i2c_block_data(client, RX8025T_SEC, sizeof(data), data);
	if (ret < 0)
		return ret; /* Keep RESET asserted after a partial write. */

	ret = i2c_smbus_write_byte_data(client, RX8025T_CTRL, ctrl);
	if (ret < 0)
		return ret;
	flags = rx8025t_read_reg(client, RX8025T_FLAG);
	if (flags < 0)
		return flags;
	return i2c_smbus_write_byte_data(client, RX8025T_FLAG,
				       flags & ~(RX8025T_VLF | RX8025T_VDET));
}

static int rx8025t_init_client(struct i2c_client *client)
{
	int flags, ctrl, ret;

	flags = rx8025t_read_reg(client, RX8025T_FLAG);
	if (flags < 0)
		return flags;
	ctrl = rx8025t_read_reg(client, RX8025T_CTRL);
	if (ctrl < 0)
		return ctrl;

	/* Disable test/timer/interrupt modes, keeping a valid retained clock. */
	ret = i2c_smbus_write_byte_data(client, RX8025T_EXT, 0);
	if (ret < 0)
		return ret;
	ctrl = (flags & RX8025T_VLF) ? RX8025T_CSEL_2S : (ctrl & (RX8025T_CSEL | RX8025T_RESET));
	ret = i2c_smbus_write_byte_data(client, RX8025T_CTRL, ctrl);
	if (ret < 0)
		return ret;
	/* Preserve voltage-invalid flags until a complete time write succeeds. */
	return i2c_smbus_write_byte_data(client, RX8025T_FLAG,
				       flags & (RX8025T_VLF | RX8025T_VDET));
}

static const struct rtc_class_ops rx8025t_ops = {
	.read_time = rx8025t_read_time,
	.set_time = rx8025t_set_time,
};

static int rx8025t_probe(struct i2c_client *client)
{
	struct rtc_device *rtc;
	int ret, flags;

	if (!i2c_check_functionality(client->adapter,
		I2C_FUNC_SMBUS_BYTE_DATA | I2C_FUNC_SMBUS_I2C_BLOCK))
		return -EOPNOTSUPP;
	ret = rx8025t_init_client(client);
	if (ret)
		return dev_err_probe(&client->dev, ret, "RTC initialization failed\n");
	flags = rx8025t_read_reg(client, RX8025T_FLAG);
	if (flags < 0)
		return flags;
	if (flags & (RX8025T_VLF | RX8025T_VDET))
		dev_warn(&client->dev, "RTC time invalid; set correct UTC time with hwclock\n");

	rtc = devm_rtc_allocate_device(&client->dev);
	if (IS_ERR(rtc))
		return PTR_ERR(rtc);
	rtc->ops = &rx8025t_ops;
	rtc->range_min = RTC_TIMESTAMP_BEGIN_2000;
	rtc->range_max = RTC_TIMESTAMP_END_2099;
	clear_bit(RTC_FEATURE_ALARM, rtc->features);
	return devm_rtc_register_device(rtc);
}

static const struct of_device_id rx8025t_of_match[] = {
	{ .compatible = "epson,rx8025t" },
	{ }
};
MODULE_DEVICE_TABLE(of, rx8025t_of_match);
static const struct i2c_device_id rx8025t_id[] = {
	{ "rx8025t", 0 },
	{ }
};
MODULE_DEVICE_TABLE(i2c, rx8025t_id);
static struct i2c_driver rx8025t_driver = {
	.driver = {
		.name = "rtc-rx8025t",
		.of_match_table = rx8025t_of_match,
	},
	.probe = rx8025t_probe,
	.id_table = rx8025t_id,
};
module_i2c_driver(rx8025t_driver);
MODULE_DESCRIPTION("MYIR RX-8025T RTC driver, direct register addressing");
MODULE_AUTHOR("MYIR Electronics; Linux 6.12 adaptation");
MODULE_LICENSE("GPL");