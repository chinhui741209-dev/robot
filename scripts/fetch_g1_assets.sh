#!/usr/bin/env bash
# 取得 Unitree G1 的 URDF + STL meshes 給 Demo Studio 的 3D 數位分身使用。
# 來源：unitreerobotics/unitree_ros (robots/g1_description)，sparse checkout 只取 g1。
# 產物：gui/assets/g1/{g1_29dof.urdf, meshes/*.STL}（離線、不上雲；assets 由 demo_studio.py 服務）。
#
# 用法：bash scripts/fetch_g1_assets.sh   （從 repo 根目錄；可重複執行）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_ROOT/gui/assets/g1"
URDF="g1_29dof.urdf"

if [ -f "$DEST/$URDF" ] && [ -d "$DEST/meshes" ]; then
  echo "[fetch_g1_assets] 已存在 $DEST/$URDF 與 meshes/，略過。要重抓請先刪除 $DEST。"
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "[fetch_g1_assets] sparse-clone unitree_ros/robots/g1_description ..."
git -C "$TMP" clone --depth 1 --filter=blob:none --sparse \
  https://github.com/unitreerobotics/unitree_ros.git ur >/dev/null 2>&1
git -C "$TMP/ur" sparse-checkout set robots/g1_description >/dev/null 2>&1

SRC="$TMP/ur/robots/g1_description"
if [ ! -f "$SRC/$URDF" ]; then
  echo "[fetch_g1_assets] 錯誤：$SRC/$URDF 不存在（上游結構可能變動）。" >&2
  exit 1
fi

mkdir -p "$DEST/meshes"
cp "$SRC/$URDF" "$DEST/$URDF"
cp "$SRC"/meshes/*.STL "$DEST/meshes/" 2>/dev/null || cp -r "$SRC"/meshes/* "$DEST/meshes/"
echo "[fetch_g1_assets] 完成：$DEST/$URDF + $(ls "$DEST/meshes" | wc -l | tr -d ' ') 個 mesh。"
