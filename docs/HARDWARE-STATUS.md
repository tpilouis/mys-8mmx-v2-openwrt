# Hardware validation status

POC6 baseline: user-reported successful boot, previous wired DHCP/SSH/LuCI and Wi-Fi AP operation; RTC read/write/time advancement passed with the RX8025T driver. USB Type-A read tested previously; POC6 USB Type-C enumerated 32GB media, read-only FAT mount/list, full Image SHA256 and unmount passed. No USB write/endurance claim. RTC backup retention has not been tested because a battery was not fitted. NOR boot work is deferred.

Hardware tests are user-run with serial output supplied to the project. Offline user-mode tests do not emulate the kernel or peripheral electrical behavior.
