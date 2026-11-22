// SPDX-License-Identifier: GPL-2.0-only
// Copyright (C) 2026 Louis Chou
/* Read-only Clause 22 diagnostic utility. No PHY register writes. */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <linux/sockios.h>
#include <linux/mii.h>
int main(int argc, char **argv) {
    struct ifreq req = {0};
    struct mii_ioctl_data *mii = (void *)&req.ifr_data;
    int fd = socket(AF_INET, SOCK_DGRAM, 0), reg, bad = 0;
    if (fd < 0) { perror("socket"); return 1; }
    snprintf(req.ifr_name, IFNAMSIZ, "%s", argc > 1 ? argv[1] : "eth0");
    if (ioctl(fd, SIOCGMIIPHY, &req) < 0) { perror("SIOCGMIIPHY"); close(fd); return 1; }
    printf("PHY address %u, Clause 22 register dump (read-only)\n", mii->phy_id);
    for (reg = 0; reg < 32; reg++) {
        mii->reg_num = reg;
        if (ioctl(fd, SIOCGMIIREG, &req) < 0) { perror("SIOCGMIIREG"); bad = 1; break; }
        printf("reg %02x = %04x\n", reg, mii->val_out);
    }
    close(fd);
    return bad;
}
