#!/usr/bin/env bash
# 一鍵啟動 Demo Studio：停舊 → 啟動（相機 + BrainAgent 視覺 + 整台 G1 3D）→ 自動開瀏覽器。
# 在 Orin 桌面或 SSH 皆可用（--open 會鎖 DISPLAY=:0 開在 Orin 螢幕）。
#
# 用法：bash scripts/run_demo.sh [PORT]   （預設 8094）
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-8094}"

# 停掉舊的（用括號技巧避免比中自己）
pkill -f "[d]emo_studio.py" 2>/dev/null || true
sleep 1

cd "$REPO"
# 用較強的 Gemini 模型提升辨識率（可由外部 env 覆蓋）；多幀重試次數亦可調。
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-pro}"
export BRAIN_DETECT_RETRIES="${BRAIN_DETECT_RETRIES:-3}"
echo "[run_demo] 啟動 Demo Studio :$PORT（相機 + BrainAgent(gemini=$GEMINI_MODEL) + G1 3D，自動開瀏覽器）"
exec python3 gui/demo_studio.py --port "$PORT" --open
