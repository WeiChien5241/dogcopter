#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PKG_DIR="$(dirname "$SCRIPT_DIR")"
PX4_DIR="${HOME}/PX4-Autopilot"

echo "Setting up flight_robot symlinks..."

# Link flight_robot model
ln -sf "${PKG_DIR}/models/flight_robot" \
       "${PX4_DIR}/Tools/simulation/gz/models/flight_robot"

# Link airframe (source)
ln -sf "${PKG_DIR}/airframes/4002_gz_flight_robot" \
       "${PX4_DIR}/ROMFS/px4fmu_common/init.d-posix/airframes/4002_gz_flight_robot"

# Link airframe (build directory)
mkdir -p "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes"
ln -sf "${PKG_DIR}/airframes/4002_gz_flight_robot" \
       "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes/4002_gz_flight_robot"

echo ""
echo "Setup complete!"
echo "Now run: cd ${PX4_DIR} && make px4_sitl gz_flight_robot"
