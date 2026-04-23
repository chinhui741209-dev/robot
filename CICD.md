# Orin CI/CD 自動化部署指引

此文件說明如何將 Jetson Orin 設定為 GitHub Self-hosted Runner，以實現自動化部署。

## 快速安裝指令 (在 Orin 上執行)

請在 Orin 的終端機複製並執行以下指令。這會下載專案中的設定腳本並開始執行：

```bash
# 1. 下載設定腳本 (請確保您的專案已公開或已設定存取權限)
curl -O https://raw.githubusercontent.com/chinhui741209-dev/robot/main/scripts/setup_orin_runner.sh

# 2. 賦予執行權限
chmod +x setup_orin_runner.sh

# 3. 執行腳本
./setup_orin_runner.sh
```

## 執行腳本時需要準備的事項

當腳本執行到一半時，會詢問您輸入 **GitHub Personal Access Token (PAT)**。

請至 GitHub 網頁產生一組具有 `repo` 權限的 PAT：
1. 點擊右上角大頭貼 > `Settings` > 左側最下方 `Developer settings` > `Personal access tokens` > `Tokens (classic)`。
2. 點擊 `Generate new token (classic)`。
3. 為 Token 命名（例如：`Orin Runner Setup`）。
4. 在 **Select scopes** 區塊，勾選 **`repo`** (Full control of private repositories)。
5. 點擊最下方的 `Generate token`，然後將顯示的字串複製下來。腳本執行時會需要貼上這串 Token。
（這個 Token 只是用來呼叫 API 取得單次的 Runner 註冊碼，註冊完成後可以隨時刪除該 PAT。）

## 腳本自動完成的工作

- **Sudo 權限**: 自動在 `/etc/sudoers.d/` 建立設定，允許 Runner 無密碼重啟 `robot-core.service`。
- **Runner 安裝**: 自動偵測 ARM64 架構並下載 GitHub Actions Runner。
- **服務化**: 將 Runner 註冊為 Linux 系統服務，確保開機後自動執行並保持連線。

## 自動部署流程說明

一旦設定完成，每當您從開發電腦推送 (Push) 程式碼到 `main` 分支時：
1. GitHub Actions 會通知 Orin。
2. Orin 會拉取最新程式碼並同步到 `/home/nvidia/poc/poc-orin`。
3. Orin 會自動執行 `sudo systemctl restart robot-core.service`。
4. 您可以從 GitHub 的 **Actions** 頁籤查看部署進度。

<!-- CI/CD Test Commit at Thu Apr 23 13:32:02 CST 2026 -->
