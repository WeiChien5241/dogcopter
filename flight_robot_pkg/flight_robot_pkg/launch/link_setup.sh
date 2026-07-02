#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PKG_DIR="$(dirname "$SCRIPT_DIR")"
PX4_DIR="${HOME}/PX4-Autopilot"

AIRFRAME="4030_gz_flight_robot"

echo "Setting up flight_robot symlinks..."

# Remove stale links from the old 4002 airframe ID
rm -f "${PX4_DIR}/ROMFS/px4fmu_common/init.d-posix/airframes/4002_gz_flight_robot" \
      "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes/4002_gz_flight_robot"

# Link flight_robot model
# -n: don't dereference an existing directory symlink (without it, re-running
# this script creates a recursive link INSIDE the model directory)
ln -sfn "${PKG_DIR}/models/flight_robot" \
        "${PX4_DIR}/Tools/simulation/gz/models/flight_robot"

# Link airframe (source)
ln -sfn "${PKG_DIR}/airframes/${AIRFRAME}" \
        "${PX4_DIR}/ROMFS/px4fmu_common/init.d-posix/airframes/${AIRFRAME}"

# Link airframe (build directory rootfs — sourced at runtime, no rebuild needed)
mkdir -p "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes"
ln -sfn "${PKG_DIR}/airframes/${AIRFRAME}" \
        "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes/${AIRFRAME}"

echo ""
echo "Setup complete!"
echo "Launch with:"
echo "  Terminal 1: python3 ${SCRIPT_DIR}/simulation-gazebo.py --world default"
echo "  Terminal 2: cd ${PX4_DIR} && \\"
echo "    PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4030 PX4_SIM_MODEL=gz_flight_robot \\"
echo "    PX4_GZ_MODELS=${PX4_DIR}/Tools/simulation/gz/models \\"
echo "    ./build/px4_sitl_default/bin/px4"
