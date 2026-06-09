#!/usr/bin/env bash
# Launch the verification dashboard stack for vision + simulation checks.
#
#   CAMERA=device (default): GUI opens /dev/video$DEVICE directly and runs its
#                            own detection; sim_sensors provides IMU only.
#   CAMERA=ros             : also launch camera_node + perception_node and the
#                            GUI subscribes /camera/image_raw + /perception/objects.
#
# Open the dashboard from any browser on the LAN:  http://<orin-ip>:$PORT
#
# Usage:  ./bringup/bringup_verify.sh
#         CAMERA=ros DEVICE=1 PORT=8088 ./bringup/bringup_verify.sh
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"
source /opt/ros/humble/setup.bash 2>/dev/null || true

CAMERA="${CAMERA:-device}"
DEVICE="${DEVICE:-1}"
PORT="${PORT:-8088}"

pids=()
cleanup() { echo "stopping verify stack..."; for p in "${pids[@]}"; do kill "$p" 2>/dev/null; done; }
trap cleanup INT TERM EXIT

# IMU source (simulated). publish_det:=false so a real camera/perception owns detections.
python3 sim/sim_sensors_node.py --ros-args -p publish_det:=false &
pids+=($!)

if [ "$CAMERA" = "ros" ]; then
  python3 perception/scripts/camera_node.py --ros-args -p device:=/dev/video${DEVICE} &
  pids+=($!)
  python3 perception/scripts/perception_node.py &
  pids+=($!)
fi

python3 gui/verify_web_gui.py --ros-args \
  -p camera:=${CAMERA} -p device:=${DEVICE} -p port:=${PORT} &
pids+=($!)

echo "===================================================================="
echo " Verify dashboard:  http://<orin-ip>:${PORT}"
echo " domain=${ROS_DOMAIN_ID}  camera=${CAMERA}  device=/dev/video${DEVICE}"
echo "===================================================================="
wait
