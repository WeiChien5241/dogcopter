#!/bin/bash
# check_links.sh for flight_robot

PX4_DIR="${HOME}/PX4-Autopilot"

echo "Checking flight_robot symlinks status..."
echo ""

check_link() {
    local path=$1
    local name=$2
    
    if [ -L "$path" ]; then
        local target=$(readlink "$path")
        echo "✓ $name"
        echo "  → $target"
    elif [ -e "$path" ]; then
        echo "⚠ $name exists but is NOT a symlink"
    else
        echo "✗ $name does not exist"
    fi
    echo ""
}

check_link "${PX4_DIR}/Tools/simulation/gz/models/flight_robot" "flight_robot model"
check_link "${PX4_DIR}/ROMFS/px4fmu_common/init.d-posix/airframes/4002_gz_flight_robot" "airframe (source)"
check_link "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes/4002_gz_flight_robot" "airframe (build)"