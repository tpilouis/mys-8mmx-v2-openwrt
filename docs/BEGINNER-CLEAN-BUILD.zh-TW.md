# Windows／WSL2 乾淨建置操作手冊（新手版）

適用：MYIR MYS-8MMX-V2、PCB V10，目前專案 POC8。編寫日期：2026-11-14。

這份手冊的目標是：新建獨立 Ubuntu → 從 GitHub 取得專案 → 下載原始碼與經同意授權的韌體 → 編譯 OpenWrt／開機元件 → 封裝 SD 映像。編譯程式並不會自動燒錄任何磁碟。

> 已完成本次環境安裝、來源下載、完整 make、SD 封裝與離線檢查。首次建置發現並修正一項設定順序問題。使用者已回報新映像燒錄 SD 後開機 PASS；本手冊及修正目前保存在本機，尚未推送 GitHub。

## 1. 先認識三個位置

| 位置／工具 | 用途 |
|---|---|
| Windows PowerShell | 安裝、啟動及管理 WSL |
| MYIR-Clean Ubuntu 終端機 | Git、Python、Docker 及建置指令 |
| 板子的串口終端機 | SD 卡開機後的硬體測試 |

**不要在板子上編譯，也不要把 Linux 指令貼到 PowerShell。** 指令區塊只複製命令本身，不要複製畫面中的提示符號。

本次目錄：

- `D:\WSL\MYIR-Clean`：WSL 的 ext4.vhdx；Linux 系統、Docker 和編譯資料都存放在這個虛擬磁碟內。
- `D:\MYIR-Clean\logs`：供 Windows 查看本次操作記錄。
- Ubuntu 的 `~/work/mys-8mmx-v2-openwrt`：從 GitHub clone 的專案。
- 專案內 `.work/openwrt`：由腳本下載、套用補丁的 OpenWrt 原始碼與編譯目錄。
- 專案內 `output`：後續封裝的 SD 映像；不納入 Git。

Windows 的 D: 是 NTFS，但真正的建置工作在 WSL 虛擬磁碟內的 **Linux ext4**；不要改成直接在 `/mnt/d` 的 NTFS 目錄進行 OpenWrt make。

## 2. PC 先決條件

- Windows 11 x64（amd64/x86_64）／已啟用虛擬化及 WSL2；本次使用 WSL 3.0.5。ARM 版 Windows 不在本次驗證範圍。
- 建議 16 GB 以上記憶體，32 GB 較充裕；D: 建議至少 100 GB 可用空間。
- 穩定網路，可連 GitHub、Ubuntu、Docker、OpenWrt 來源站。
- 第一次下載與工具鏈編譯可能花數小時；中途不要休眠、關機或強制終止 WSL。
- 目前 repo 為 Private，需有存取權。瀏覽器已登入，不一定表示 Ubuntu 的 Git 已有認證。
- 新環境不需要先安裝 Yocto、NXP SDK 或 ARM 交叉工具鏈。OpenWrt 會在建置中建立它需要的工具鏈。

既有 `MYIR-Dev` 與板上已驗證映像請保留。本流程不使用它的原始碼、Docker 映像、工具鏈或 `dl` 下載快取。

## 3. 建立 MYIR-Clean（PowerShell）

先檢查：

```powershell
wsl --version
wsl --list --verbose
Get-Volume -DriveLetter D
```

如果 Windows 尚未啟用 WSL，先依 Microsoft 文件以系統管理員 PowerShell 安裝 WSL 功能，完成要求的重開機，再回到這裡。不要把舊的 Ubuntu 環境刪除重裝。

本次使用以下命令建立新環境：

```powershell
New-Item -ItemType Directory -Force D:\MYIR-Clean\logs
wsl --install Ubuntu-24.04 --name MYIR-Clean --location D:\WSL\MYIR-Clean --no-launch --web-download
wsl --list --verbose
```

成功判斷：清單出現 `MYIR-Clean`、VERSION 是 `2`，D: 指定資料夾內有 `ext4.vhdx`。

- 若提示 `--name` 或 `--location` 不支援，先更新 WSL，再查看 `wsl --help`；不要自行改成覆蓋既有發行版。
- 若名稱已存在，停止這一步；不要使用 `wsl --unregister`，該命令會刪除整個環境及其資料。
- 安裝器取得的 Ubuntu 24.04 小版本可能隨日期更新；本次實際為 24.04.5 LTS。

## 4. 建立 Linux 使用者與安裝工具（Ubuntu root）

在 PowerShell 開啟新環境的 root 終端機：

```powershell
wsl -d MYIR-Clean -u root -- bash
```

以下改在 **Ubuntu root** 執行：

```bash
cat /etc/os-release
getent passwd 1000
```

本次全新環境尚無 UID 1000 帳號，因此建立 `myir`：

```bash
useradd -m -u 1000 -s /bin/bash -G sudo myir
```

若 UID 1000 已被占用，不要直接刪除帳號；先確認安裝器是否已替你建立使用者。編譯容器目前使用 UID/GID 1000，建置目錄必須允許該 UID 寫入。

手動使用者可執行下列命令設定自己的 Linux 密碼；輸入時不顯示字元是正常現象，不要將密碼寫入腳本或 Git：

```bash
passwd myir
```

本次由自動化透過 `wsl -u root` 安裝工具，尚未設定個人的 Linux 密碼；這不影響 WSL 指定使用者啟動或 Docker 群組操作。若日後要用 `sudo`，請先設定 Linux 密碼。這與開發板的 root 密碼是兩回事。

設定此新 WSL 的 systemd 與預設使用者（僅對新建的 MYIR-Clean 執行）：

```bash
cat > /etc/wsl.conf <<'EOF'
[boot]
systemd=true
[user]
default=myir
EOF

apt-get update
apt-get install -y git python3 ca-certificates curl gnupg
```

### 安裝獨立 Docker Engine

本次在 MYIR-Clean 內安裝 Docker Engine，不連接 MYIR-Dev 或 Docker Desktop 的既有 daemon。

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker myir
systemctl enable --now docker
mkdir -p /home/myir/work
chown myir:myir /home/myir/work
exit
```

Docker 群組具有此 Linux 環境的高權限，僅加入你信任的本機帳號。

回到 **PowerShell**，重新啟動這個新環境，讓預設使用者與群組設定生效：

```powershell
wsl --terminate MYIR-Clean
wsl -d MYIR-Clean -u myir --cd ~
```

以下都在 **Ubuntu 的 myir 帳號**執行：

```bash
id
cat /etc/os-release
git --version
python3 --version
docker version
docker info --format '{{.DockerRootDir}}'
docker image ls
```

成功判斷：帳號為 UID 1000，群組包含 docker，Docker 可顯示 Client／Server，資料目錄為此環境的 `/var/lib/docker`。第一次 build 前映像清單為空。

## 5. 從 GitHub 取得專案（Ubuntu myir）

```bash
cd ~/work
git clone https://github.com/tpilouis/mys-8mmx-v2-openwrt.git
cd mys-8mmx-v2-openwrt
git rev-parse HEAD
git status --short
```

第一次使用 `git clone`，之後更新才使用 `git pull --ff-only`。不要重複 clone 到已存在且有資料的目錄。

`git pull` 只更新這個移植專案，不會自動將新補丁／overlay／設定同步到已存在的 `.work/openwrt`。若要驗證新版本，應準備新的工作目錄並調整掛載路徑。更新前先 `git status --short`，保留自己的修改，不要用強制 reset 清除它們。

### Private repo 認證

若遇到 `Repository not found` 或認證失敗，先確認帳號有權限；GitHub HTTPS 不接受帳號密碼作 Git 認證。可使用你已設定的 SSH key 或 Git Credential Manager，不要將 Token 放入 URL、操作紀錄或手冊。

本機已安裝 Git for Windows，且其 Git Credential Manager 已登入；本次只借用該認證，沒有複製舊專案或快取。若你的 PC 也符合這個條件，可在 Ubuntu 設定：

```bash
git config --global credential.helper '/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe'
```

路徑要以你的實際安裝位置為準。再重試 clone。

如果是全新 PC、還未登入 Git Credential Manager，可先安裝 Git for Windows（保留預設 GCM），然後在 PowerShell 執行：

```powershell
git ls-remote https://github.com/tpilouis/mys-8mmx-v2-openwrt.git HEAD
```

依 GCM 提示在瀏覽器登入有 repo 權限的帳號，完成後回 Ubuntu 重試。這個命令只查詢版本，不會下載整個專案。僅在瀏覽器登入 GitHub 並不一定已完成 Git 認證。如果未安裝 Git for Windows，可使用你自己的 GitHub SSH 認證方式；未來 repo 公開後，唯讀 HTTPS clone 即不需私人倉庫權限。

## 6. 準備固定版本的原始碼

確認位於 `~/work/mys-8mmx-v2-openwrt`：

```bash
pwd
cat configs/source.json
python3 tools/prepare.py
```

腳本會執行：

1. 建立 `.work/openwrt`。
2. 從官方 GitHub 取得 `configs/source.json` 指定的 OpenWrt commit。
3. 檢查並套用 `patches/myir.patch`。
4. 複製建置設定、固定 feeds 版本與 runtime overlay。
5. 從指定 MYIR 韌體 commit 下載 AP6256 韌體／校正檔，核對 SHA256。

成功判斷：顯示 `Prepared poc8`。腳本不使用舊 `MYIR-Dev`。

若提示 `Destination exists`，不要直接刪除資料；先確認先前是否已準備完成。新手第一次若需要重試，可使用 `--work` 指定另一個全新目錄，但所有後續 Docker 掛載路徑也必須一起修改。下載途中失敗的目錄不要當成已準備完成。

## 7. 建立編譯容器並執行 make

仍在 **Ubuntu myir、專案根目錄**：

```bash
mkdir -p output/logs
docker build --progress=plain -t myir/openwrt-build:noble -f tools/Dockerfile .
```

Dockerfile 會下載 Ubuntu 容器與編譯依賴。這不是沿用舊環境的 Docker 映像。

接著執行：

```bash
set -o pipefail
docker run --name myir-clean-poc8-build \
  -v "$PWD/.work/openwrt:/work" \
  -v "$PWD/tools:/setup:ro" \
  -w /work myir/openwrt-build:noble \
  bash -lc './scripts/feeds update -a && bash /setup/build-poc8.sh' \
  2>&1 | tee output/logs/firmware-build.log
```

編譯腳本目前使用 8 個平行工作：安裝 feeds → `make defconfig` → `make download -j8` → `make -j8`。OpenWrt 會建立交叉工具鏈，然後編譯核心、套件與 rootfs。

- `WARNING` 不一定代表失敗，應確認最後命令的退出碼與成功訊息。
- 終端機暫時無輸出不一定是停止，可能正在下載或連結大型檔案。
- 容器不會自動刪除，方便查看退出碼。

另一個 MYIR-Clean 終端機可查看：

```bash
docker ps -a
docker inspect myir-clean-poc8-build --format '{{.State.Status}} {{.State.ExitCode}}'
```

成功判斷：日誌末尾有 `POC8 BUILD SUCCEEDED`，容器狀態 `exited 0`。

產物位置：

```bash
ls -lh .work/openwrt/bin/targets/imx/cortexa53/
```

這一步產生核心、DTB、rootfs 等，**還不是完整 SD 開機映像**。

## 8A. 建議：完整開機元件與 SD 建置入口

本機版本已新增從原始碼建立 SPL／U-Boot／TF-A／imx-mkimage 的流程，尚未推送 GitHub。新手可在第 5 章取得包含新腳本的專案版本後，閱讀 [開機元件從零建置手冊](BOOTLOADER-FROM-SOURCE.zh-TW.md) 與 NXP 授權說明，再執行：

```bash
bash tools/build-sd.sh --accept-nxp-eula
```

只有在已閱讀並同意適用授權時才使用接受選項。這個入口包含第 6～7 章的 OpenWrt 建置及新的開機元件建置，不需要另外找舊開機檔；產物在 `output/from-zero`。已完成本次 OpenWrt make 的進階使用者可加 `--skip-openwrt`。

以下第 8B／9 章是最初乾淨測試使用外部 POC1a 的歷史／進階模式，保留供比對；新手完整入口不使用外部預編譯檔。

## 8B. 歷史模式：完整 SD 映像的外部開機檔

若選擇這個歷史／進階模式，必須另外取得：

```text
imx-boot-mys8mmx-v2-2025.04-poc1a.bin
SHA256: 42c8e8c4b256fdc819b5b20c88569e40b69f8db72ff5c6bf92e4c31790e524c0
```

它不是從 Git 倉庫下載的檔案。不要把 DDR 訓練韌體、密碼或開機二進位檔自行加入 Git。若本次封裝使用既有 POC1a 檔案，報告必須明確註記這個外部輸入；不能宣稱開機元件也已從乾淨環境重建。

將合法取得、雜湊正確的檔案放入你自己的目錄，例如 `~/private/bootloader`：

```bash
export BOOTLOADER_DIR="$HOME/private/bootloader"
sha256sum "$BOOTLOADER_DIR/imx-boot-mys8mmx-v2-2025.04-poc1a.bin"
```

此章開始前，先確認第 7 章成功。

## 9. 封裝與離線驗證

```bash
mkdir -p output
docker run --rm \
  -v "$PWD/.work/openwrt:/work:ro" \
  -v "$PWD/tools:/setup:ro" \
  -v "$PWD/output:/output" \
  -v "$BOOTLOADER_DIR:/bootloader:ro" \
  myir/openwrt-build:noble python3 /setup/compose-poc8.py

docker run --rm \
  -v "$PWD/tools:/setup:ro" \
  -v "$PWD/output:/output:ro" \
  myir/openwrt-build:noble python3 /setup/verify-poc8.py
```

腳本核對開機檔 SHA256、EXT4／FAT、分割區與 gzip 回讀，另檢查編譯後的 DTB 與模組。

額外完整分割區／檔案比對可在中間檔尚未搬移的這個流程執行：

```bash
docker run --rm \
  -v "$PWD/.work/openwrt:/work:ro" \
  -v "$PWD/tools:/setup:ro" \
  -v "$PWD/output:/output:ro" \
  myir/openwrt-build:noble python3 /setup/verify-disk-poc8.py
```

若程式報錯，停止，不要拿未驗證映像燒錄。部分歷史 ARM64 服務模擬／單元測試腳本仍含原開發機路徑與私人測試認證，不是本手冊可直接執行的通用指令。

## 10. 燒錄與第一次開機（需另行實板操作）

1. 使用備用 SD 卡；先備份卡上內容。
2. 在燒錄工具選取 `output` 內的完整 `.img.gz` 或解壓後 `.img`；仔細核對目標是 SD 卡，**不是 PC D: 或 NVMe SSD**。
3. 啟用寫入後驗證。
4. 板子斷電後插 SD 卡，接好串口，以既有 SD 開機撥碼啟動。
5. 先設定板子 root 密碼，再接一般網路。Git 匯出版本不含目前板子的密碼雜湊，Wi-Fi 預設停用。
6. 串口執行 `cat /etc/myir-build`、`ubus call system board`，確認為預期版本。
7. 檢查有線 DHCP、SSH／LuCI；有 SSD 時再執行 `myir-m2-diag`。

離線 make 成功不等於新映像已在板上驗證。第一次開機與硬體結果應另外保存。

## 11. 常見問題

| 現象 | 處理方式 |
|---|---|
| `docker: permission denied` | 確認 `id` 有 docker 群組，重開此 WSL 工作階段；不要把專案改成全員可寫 |
| 容器名稱已存在 | 用 `docker ps -a` 查看舊紀錄；新一次 run 使用另一個名稱，不要盲目清理所有容器 |
| `No space left on device` | 同時檢查 Windows D: 與 Ubuntu `df -h /`；虛擬磁碟顯示容量大，不代表實體 D: 還有空間 |
| `Killed`／退出碼 137 | 可能記憶體不足，查看記錄；將 `tools/build-poc8.sh` 內兩個 `-j8` 改為 `-j4`，使用新容器名稱重試 |
| 下載逾時或 hash mismatch | 保留日誌，重試原版本；不要任意更換版本或停用校驗 |
| `bad interpreter`／`^M` | 確認檔案使用 LF 換行；不要用 Windows 編輯器另存成 CRLF |
| Git 套用補丁失敗 | 核對固定 OpenWrt commit；不要直接換成最新 main |
| `ROOT`／權限錯誤 | 編譯應在容器的 builder UID 1000 執行，而非 root |
| `Cannot connect to Docker daemon` | 在新環境檢查 `systemctl status docker` 與 systemd 是否啟用 |

## 12. 本次驗證紀錄

| 項目 | 狀態 |
|---|---|
| D: 空間 | 開始前約 389.5 GiB 可用 |
| 獨立 WSL | 已建立 MYIR-Clean，Ubuntu 24.04.5，位於 D: |
| 基本工具／Docker | 已通過，原始映像清單為空 |
| GitHub 重新 clone | 已完成；起始 commit `68ac78128c6b8fe1d0e32a59bfb027f94fb34aa4` |
| 全新來源下載與補丁 | 已完成，OpenWrt commit `71dbef3fd854850a810c93416c16d32d3fc82734` |
| 全新 Docker 編譯映像 | 已完成，從 Docker Hub 與套件站全新建立 |
| 完整 make | 通過：修正 LuCI 設定順序後，從全新來源建立主機工具、GCC 14.3.0、核心與套件，容器退出碼 0 |
| 完整 SD 封裝／離線驗證 | 通過：EXT4／FAT、分割區回讀、913 個一般檔案與 tar 比對、gzip、SHA256 |
| 本次新映像實板測試 | 2026-11-14 使用者回報：SD 開機、DHCP Client、USB、SSD PASS；其餘未回報重測 |

本次記錄位置：`D:\MYIR-Clean\logs`。產物已另複製至 `D:\MYIR-Clean\output`，其中 `clean-build-report.json` 記錄來源、修正、校驗與外部開機檔。密碼／Token 不應出現在日誌、Git 或截圖。

本次自動化將日誌存至 Windows 的 `D:\MYIR-Clean\logs`；手動執行第 7 章則使用專案內 `output/logs`。本次重要日誌如下：

| 日誌 | 結果 |
|---|---|
| `bootstrap-host.log` | Ubuntu 工具／Docker 安裝成功 |
| `clone-prepare.log` | 從 GitHub 取得專案、下載並套用固定來源成功 |
| `docker-build.log` | 全新編譯容器建立成功 |
| `firmware-build.log` | **首次失敗**，LuCI 選項在 feeds 初始階段遺失；保留供追查 |
| `firmware-build-retry1.log` | **修正後完整 make 成功** |
| `compose.log` | SD 映像封裝及基礎檢查通過 |
| `artifact-check.log` | DTB／模組／網路與周邊設定檢查通過 |
| `final-disk-check.log` | 最終映像分割區、rootfs 檔案、壓縮回讀與校驗通過 |

### 本次發現的乾淨建置問題

初始 GitHub commit 的流程在 `feeds update/install` 後才執行 `make defconfig`，但第一次建立 feeds metadata 時，先前 `.config` 內尚未被辨識的 feed 選項會被移除；其中 `luci-ssl` 因而變成未選，建置腳本的必要條件檢查退出。這不是下載快取缺少或板子故障。

修正：在 feeds 安裝完成後，從 `/work/myir-diffconfig` 重新載入固定設定，再執行最終 `make defconfig`。可透過 `MYIR_CONFIG_SEED` 指定另一份完整設定種子；直接修改 `.config` 可能在此步被覆寫。第一個失敗容器與日誌保留，後續使用新容器名稱測試。

本次重新下載來自 GitHub 的起始版本為 `68ac781`；重試使用本次本機修正的 `tools/build-poc8.sh`。在修正正式上傳前，不可宣稱 GitHub 該舊 commit 無修改即可完成乾淨建置。


### 本次外部輸入與結果範圍

本次 SD 封裝使用原開發機另行保存、重新核對 SHA256 的 POC1a 開機檔，複製至新環境的 `/home/myir/private/bootloader`。只有這個已明示的開機檔沿用；OpenWrt 原始碼、feeds、工具鏈、Docker 映像與下載快取皆沒有取自舊環境。因此本次證明的是「乾淨重建 OpenWrt ＋ 提供既有開機檔即可封裝 SD」，不是整套 NXP 開機鏈從原始碼重建。

新映像的 SHA256 請使用同資料夾的 `SHA256SUMS.txt`，不要沿用舊 POC8 映像的雜湊。新版本不含舊 root 密碼；編譯容器的 hostname／GNU build-id 等中繼資訊也可能不同。本次 DTB 與先前 POC8 完全相同，核心設定相同；完整核心二進位在正規化容器 hostname 與 GNU build-id 後相同。這不代表整個 SD 映像逐位元相同。

本次未執行需要舊私人密碼測試資料的 ARM64 SSH／LuCI 模擬。編譯和靜態檢查成功，也不能代替新映像的實板開機、網路與 SSD 測試。

## 13. 官方參考

- [Microsoft WSL 指令](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
- [Ubuntu WSL 安裝](https://ubuntu.com/wsl/docs/latest/howto/install-ubuntu-wsl2/)
- [Docker Engine Ubuntu 安裝](https://docs.docker.com/engine/install/ubuntu/)
- [WSL Git 與 Git Credential Manager](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-git)
- [本專案 README](../README.md)
### 2026-11-14 實板開機結果

使用者將本次乾淨建置的映像燒錄至 SD 卡，回報開機測試 PASS。至此已完成「新環境下載來源＋本次設定順序修正＋完整 make＋外部 POC1a 開機檔封裝＋SD 實板開機」流程。這不代表 NXP 開機鏈已從頭重建，也不代表本次映像的網路、SSH／LuCI、Wi-Fi、USB、RTC、NVMe 與長時間穩定性已全部重測。

### 2026-11-14 DHCP Client 結果

使用者回報本次乾淨建置映像 DHCP Client 測試 PASS。已確認項目為 SD 開機及 DHCP Client；SSH／LuCI、Wi-Fi、USB、RTC、NVMe 與長時間穩定性尚未回報本次映像的重測結果。

### 2026-11-14 USB／SSD 結果

使用者回報本次乾淨建置映像 USB／SSD 測試 PASS，未另提供端口、協商速度、讀寫方式、雜湊或效能數據。因此僅記錄本次功能測試通過，不延伸為所有 USB 端口、Gen2 速度、寫入、效能或耐久性驗證。累計已確認 SD 開機、DHCP Client、USB、SSD；SSH／LuCI、Wi-Fi、RTC 尚未回報本次映像的重測結果。

## 14. 後續整合開機元件

已新增來源固定、授權接受、下載、編譯及 SD 封裝整合入口，詳見第 8A 章及開機元件手冊。前述 2026-11-14 第一輪紀錄仍如實保留為「外部 POC1a」測試；新整合產物另行記錄，不把舊映像的實板 PASS 轉移給新建置的開機檔。

### 2026-11-14 新開機元件流程與實板結果

第 8A 章為目前建議的新手入口，涵蓋 OpenWrt 與 SPL／U-Boot／TF-A／imx-mkimage。詳細的 WSL 開啟方式、開機元件獨立建置指令、固定日期解釋及實板驗證步驟，已整理於 [開機元件從零建置手冊](BOOTLOADER-FROM-SOURCE.zh-TW.md)。第 8B 章與先前測試記錄保留為舊外部開機檔模式。

本次從原始碼重建的開機檔（SHA256 `53ad61e8ab66ec0740a8126f2fe466697a9d27a7c61d4522e3b2bf5539e5a1c0`）已實際開機進入 OpenWrt。插入 SSD 後確認 PCIe Gen2 x1，NVMe FAT 唯讀掛載、全檔雜湊及卸載通過。這份紀錄獨立於前述使用舊開機檔的測試；不延伸為新映像的所有周邊或穩定性均通過。
