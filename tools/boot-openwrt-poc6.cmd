# MYIR MYS-8MMX-V2 POC6 RTC USB Host: SD + wired DHCP + RTC USB candidate.
echo "MYIR OpenWrt 25.12.6 POC6 Type-C Host candidate - hardware test pending"
setenv kernel_addr_r 0x42000000
setenv fdt_addr_r 0x46000000
setenv bootargs console=ttymxc1,115200 earlycon=ec_imx6q,0x30890000,115200 root=PARTUUID=4d595232-02 rootfstype=ext4 rootwait rw
if fatload mmc ${mmcdev}:1 ${kernel_addr_r} Image; then
    if fatload mmc ${mmcdev}:1 ${fdt_addr_r} imx8mm-mys-8mmx-v2.dtb; then
        booti ${kernel_addr_r} - ${fdt_addr_r}
    fi
fi
echo "OpenWrt did not start; check serial output and SD files."
