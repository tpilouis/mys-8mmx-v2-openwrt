# 從原始碼建立 SPL／U-Boot／TF-A 與完整 SD 映像

更新：2026-11-14。適用 MYS-8MMX-V2 V10／POC8。這個流程取得所需元件、編譯開源部分，並下載 NXP 專有 DDR 訓練韌體；不代表專有韌體也有公開原始碼。

本機已完成整合與離線測試，尚未推送 GitHub。新開機檔與 SD 映像已由使用者確認進入 OpenWrt shell；周邊及重啟穩定性仍待驗證。先前使用外部 POC1a 檔的乾淨映像測試結果不能直接移作這個新映像的測試結果。

## 1. PC 環境

先完成 [新手乾淨建置操作手冊](BEGINNER-CLEAN-BUILD.zh-TW.md) 第 1～5 章：Ubuntu 24.04 amd64／WSL2、Git、Python 3、獨立 Docker、UID 1000 使用者及 GitHub 專案 clone。請在 Ubuntu 終端機、專案根目錄執行以下指令，不是在板子或 PowerShell 裡執行。

## 2. 先閱讀韌體授權

閱讀 [NXP 韌體說明](../bootloader/NXP-FIRMWARE-NOTICE.md) 及適用協議。DDR .bin 不是開源元件，必須自行同意授權才能下載使用。不同意就不要執行帶有接受選項的命令。

套件由 NXP 官方網址下載；版本、完整套件雜湊、COPYING／SCR 雜湊及四個 DDR 檔案雜湊固定於 [sources.json](../bootloader/sources.json)。腳本不會執行 NXP 自解壓程式，不會省略校驗，也不會在沒有接受選項時下載或解出韌體。

對已自行合法取得的套件，可只顯示其確切授權／內容清單：

```bash
python3 tools/prepare-bootloader.py --show-license \
  --firmware-archive /absolute/path/firmware-imx-8.7.bin
```

## 3. 新手完整入口

在你閱讀並同意適用條款後：

```bash
bash tools/build-sd.sh --accept-nxp-eula
```

它依序執行：

1. 建立編譯 Docker 映像。
2. 準備固定版本 OpenWrt，更新／安裝固定 feeds，編譯工具鏈、Linux、套件及 rootfs。
3. 從 NXP 官方下載 firmware-imx-8.7，校驗後只取四個 DDR 訓練韌體與授權文件。
4. 從 NXP GitHub 取得固定版本 U-Boot、TF-A、imx-mkimage，檢查 tag 對應 commit。
5. 套用 MYIR 板級 patch；核對原廠 DDR timing 未變更。
6. 使用本次 OpenWrt 建立的 GCC 14.3.0 工具鏈編譯 SPL／U-Boot／TF-A。
7. 使用 imx-mkimage 打包，檢查 ROM header、SPL、FIT、BL31 與內嵌 DDR 資料。
8. 依本次建置報告驗證開機檔，封裝 SD 映像，再檢查檔案系統、分割區、rootfs 檔案及壓縮回讀。

**不需要另外取得舊 POC1a 開機檔，不需要安裝整套 Yocto，也不會自動燒錄 SD／eMMC／NOR。**

如果已成功完成這份專案的 OpenWrt make、只是要重建開機元件，可使用進階選項：

```bash
bash tools/build-sd.sh --accept-nxp-eula --skip-openwrt
```

第一次從零執行不要用 `--skip-openwrt`。此選項不會建立缺少的工具鏈；缺少必要產物會停止。

## 4. 產物與成功標準

| 位置 | 內容 |
|---|---|
| `.work/openwrt` | OpenWrt 來源與自行產生的交叉工具鏈 |
| `.work/bootloader` | 三個開機元件來源、DDR 韌體與編譯目錄 |
| `.work/downloads` | 校驗後的 NXP 原始下載套件 |
| `output/bootloader` | 開機檔、SPL／BL31／FIT、設定與建置證明 |
| `output/from-zero` | 完整 SD `.img`／`.img.gz` 與檢查報告 |
| `output/logs` | 各次 Docker、make、封裝與檢查的時間戳記日誌 |

最終應顯示：

```text
FROM-SOURCE SD BUILD AND OFFLINE CHECKS PASSED: output/from-zero
```

SD 檔名：`openwrt-25.12.6-mys-8mmx-v2-sd-nvme-poc8.img.gz`。

`output/bootloader/bootloader-build.json` 記錄本次來源、DDR 雜湊、開機檔 SHA256 與檢查結果。封裝程式會核對它與專案的固定版本政策；不能拿任意 .bin 或只改 JSON 裡的來源版本蒙混封裝。這是本機建置一致性檢查，不是第三方數位簽章認證。

這個流程也保留相容舊外部 POC1a 檔案的手動封裝模式：未提供建置證明時，只接受原先指定的舊 SHA256；新手完整入口不使用此模式。

## 5. 固定版本

| 元件 | Commit |
|---|---|
| NXP U-Boot 2025.04 | `4ddbad60eff308a5b356fb9ab8734ac382ddd692` |
| NXP TF-A v2.12 | `a266ff458c2526a6474036a5c6648be6fdc54fe3` |
| NXP imx-mkimage | `be80fadd5e7988214149a2bc48daac1b0950d4c2` |

共同 release tag：`lf-6.12.49-2.2.0`。tag 若不再對應指定 commit，腳本會停止，不改用最新版。

板級修改保存在 `bootloader/uboot-myir.patch`，包含原廠 GPL DDR timing，原始著作權／授權標示保留。timing SHA256：`d93343afc0b74b553ba4b3f210c40a945edc43ea75dac8ebca0864e8712ab8cd`。不重新產生 timing，也沒有取消每次冷開機的訓練。

建置時間固定為原 POC1a 的 SOURCE_DATE_EPOCH；不同工具鏈產生的版本字串等仍可能讓檔案 SHA256 與舊預編譯檔不同。因此新流程使用固定來源＋檢查報告＋實際輸出雜湊，不要求輸出一定等於舊檔。

## 6. 失敗與重試

- 未帶接受授權選項：在下載前退出，這是預期行為。
- NXP 網站無法下載：保留錯誤，勿更換來源版本或跳過 SHA256。可先合法下載指定套件，再用 `prepare-bootloader.py --accept-nxp-eula --firmware-archive /path/file`；之後整合入口仍需使用同一固定套件／快取。
- 下載中斷：`.part` 不會當成完成檔；重新執行會重新下載未完成的套件。
- 完整檔 hash mismatch：停止並核對下載來源，勿自行修改 manifest 遷就檔案。
- tag／commit／patch 不符：停止，保留自己的修改；選擇新的工作目錄或先調查，不要使用強制 reset／清除全部資料。
- 原始碼編譯失敗：修正問題後可重跑，重用本次自行建立的快取；這不是引用舊 MYIR-Dev 快取。
- 新版本 patch 與已有 `.work/openwrt` 不相容：入口會停止。不要以為 `git pull` 會自動移植既有工作樹。
- 上次已生成的映像即使還在，**本次命令失敗時也不要當成本次成功輸出**。先確認完整成功訊息與當次日誌。

## 7. 開機元件的保護性測試（開發者／維護者）

在本機開機檔建置完成後：

```bash
MYIR_TEST_BOOTLOADER_DIR="$PWD/output/bootloader" \
  python3 -m unittest discover -s tests -v
```

測試包含：缺少接受授權選項時不建置；拒絕被改過的開機資料、來源 commit 或建置政策。沒有先建置產物而未設定環境變數時，產物測試會 skip，不代表完整驗證通過。本次六項均實際執行通過。

## 8. 本次實際驗證範圍

- 原先已在獨立 MYIR-Clean 從空白工具鏈／Docker 下載與編譯 OpenWrt，結果及必要修正見乾淨建置手冊。
- 本次開機工作目錄及 DDR 下載快取原先不存在；已重新下載三個 Git 專案與 NXP 官方套件，沒有取用 MYIR-Dev 的開機二進位檔／來源快取。
- 新 SPL／U-Boot／TF-A／imx-mkimage 編譯、DDR 與封裝結構檢查通過。
- 整合入口的略過 OpenWrt 模式、預設完整模式與最終 SD 靜態檢查皆已執行通過。預設模式中的 OpenWrt 部分重用本次 MYIR-Clean 自行建立的快取；並未為這次整合再次安裝整個 WSL。
- 新開機檔 SHA256 與舊 POC1a 不同；**新映像已確認開機至 OpenWrt shell，周邊與穩定性仍待確認**。先前已測試的映像會保留。

## 9. 實板操作

先備份設定，使用另一張 SD 卡，核對新映像 SHA256，啟用燒錄工具的寫入後驗證。板子斷電後換卡，上電保留完整串口文字，確認 SPL DDR calibration、U-Boot 2025.04、2 GiB DRAM、boot.scr 與 Linux 正常啟動，再測 DHCP／USB／SSD。不要先寫 eMMC、NOR 或 fuse。
## 10. 新開機鏈實板結果

2026-11-14 使用者確認新 boot SHA256 為 53ad61e8 開頭，並提供完整後續核心紀錄：DDR 校準完成、2 GiB、SD 讀取、EXT4 root 掛載及 OpenWrt shell 通過。早先 boot.scr 後的一次重啟原因仍待確認，不標記重啟穩定性通過。本次 PCIe 未連線，需先確認是否安裝 SSD；DHCP、USB／SSD I/O 與 Wi-Fi 尚未回報此新映像測試結果。開機顯示 root 尚未設密碼，請先在串口執行 `passwd`。
