# Orin GUI 自動啟動與部署指南 (最終解決方案)

本指南說明如何解決背景服務無法開啟桌面視窗的問題，並實現 GUI 的自動啟動。

## 1. 同步程式碼與建立自動啟動設定

請在 **Orin 終端機** 執行以下指令，將設定檔連結到系統的桌面自動啟動目錄：

```bash
cd /home/nvidia/poc/poc-orin
# 強制同步 GitHub 最新程式碼
git fetch origin
git reset --hard origin/main

# 建立桌面自動啟動目錄 (如果還沒有的話)
mkdir -p /home/nvidia/.config/autostart

# 建立捷徑連結
ln -sf /home/nvidia/poc/poc-orin/services/autostart/robot-gui.desktop /home/nvidia/.config/autostart/
```

## 2. 測試與生效

### A. 測試 GUI 程式是否正常
在目前的桌面環境直接執行以下指令。如果視窗能正常彈出，代表程式與權限皆正確：
```bash
/usr/bin/python3 /home/nvidia/poc/poc-orin/gui/scripts/demo_gui_tk.py
```
*(確認後可關閉視窗)*

### B. 重啟核心背景服務
核心運算與感知邏輯仍由 systemd 管理：
```bash
sudo systemctl restart robot-core.service
```

### C. 驗證自動啟動
由於 `autostart` 是在進入桌面環境時觸發，您可以嘗試：
- **登出並重新登入** Orin。
- 或者直接**重啟 Orin**。

登入後，GUI 監控視窗將會自動跳出來。

## 3. 未來開發流程

1. 在 **Mac 端** 修改程式碼（GUI 或核心邏輯）。
2. 使用 `git push` 上傳。
3. **Orin 端** 會自動拉取程式碼並重啟核心服務。
4. 如果修改的是 GUI 程式碼，請手動重啟 GUI 視窗或重新登入即可。
