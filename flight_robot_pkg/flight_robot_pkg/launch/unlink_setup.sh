#!/bin/bash
# unlink_setup.sh for flight_robot

PX4_DIR="${HOME}/PX4-Autopilot"

echo "Removing flight_robot symlinks..."

# Remove model symlink
if [ -L "${PX4_DIR}/Tools/simulation/gz/models/flight_robot" ]; then
    rm "${PX4_DIR}/Tools/simulation/gz/models/flight_robot"
    echo "✓ Removed flight_robot model symlink"
fi

# Remove airframe symlink (source)
if [ -L "${PX4_DIR}/ROMFS/px4fmu_common/init.d-posix/airframes/4002_gz_flight_robot" ]; then
    rm "${PX4_DIR}/ROMFS/px4fmu_common/init.d-posix/airframes/4002_gz_flight_robot"
    echo "✓ Removed airframe symlink (source)"
fi

# Remove airframe symlink (build)
if [ -L "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes/4002_gz_flight_robot" ]; then
    rm "${PX4_DIR}/build/px4_sitl_default/rootfs/etc/init.d-posix/airframes/4002_gz_flight_robot"
    echo "✓ Removed airframe symlink (build)"
fi

echo "Done! All flight_robot symlinks removed."
