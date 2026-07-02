"""DogCopter GROUND/FLIGHT mode arbitration.

GROUND: teleop /cmd_vel is forwarded to the wheels (/wheel/cmd_vel, bridged
to the Gazebo DiffDrive plugin); PX4 is left alone.
FLIGHT: wheel commands are dropped, PX4 arms and takes off via uXRCE-DDS.

Service /dogcopter/set_flight_mode (std_srvs/SetBool): true = fly,
false = land. The response only acknowledges the request; transitions are
asynchronous — watch /dogcopter/mode (std_msgs/String) for completion.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
    HistoryPolicy,
)

from geometry_msgs.msg import Twist
from std_msgs.msg import String
from std_srvs.srv import SetBool

from px4_msgs.msg import VehicleCommand, VehicleStatus, VehicleLandDetected

GROUND = 'GROUND'
TAKING_OFF = 'TAKING_OFF'
FLIGHT = 'FLIGHT'
LANDING = 'LANDING'

TRANSITION_TIMEOUT_S = 30.0
ARM_RETRY_HINT_COUNT = 3


class ModeManager(Node):

    def __init__(self):
        super().__init__('mode_manager')

        # PX4 uXRCE-DDS convention
        px4_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.state = GROUND
        self.arming_state = None
        self.nav_state = None
        self.landed = None
        self.transition_elapsed = 0.0
        self.arm_retries = 0

        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.on_cmd_vel, 10)
        self.wheel_pub = self.create_publisher(Twist, '/wheel/cmd_vel', 10)
        self.mode_pub = self.create_publisher(String, '/dogcopter/mode', 10)

        self.vehicle_command_pub = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', px4_qos)
        self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status_v1',
            self.on_vehicle_status, px4_qos)
        self.create_subscription(
            VehicleLandDetected, '/fmu/out/vehicle_land_detected',
            self.on_land_detected, px4_qos)

        self.create_service(
            SetBool, '/dogcopter/set_flight_mode', self.on_set_flight_mode)

        self.timer = self.create_timer(1.0, self.on_timer)
        self.get_logger().info('mode_manager up, state=GROUND')

    # --- teleop passthrough -------------------------------------------------

    def on_cmd_vel(self, msg: Twist):
        if self.state == GROUND:
            self.wheel_pub.publish(msg)

    def stop_wheels(self):
        # DiffDrive holds the last command; explicitly zero it on GROUND exit.
        self.wheel_pub.publish(Twist())

    # --- PX4 feedback ---------------------------------------------------------

    def on_vehicle_status(self, msg: VehicleStatus):
        self.arming_state = msg.arming_state
        self.nav_state = msg.nav_state

    def on_land_detected(self, msg: VehicleLandDetected):
        self.landed = msg.landed

    # --- service ---------------------------------------------------------------

    def on_set_flight_mode(self, request, response):
        want_flight = request.data
        if want_flight and self.state == GROUND:
            self.enter(TAKING_OFF)
            response.success = True
            response.message = 'takeoff requested; watch /dogcopter/mode'
        elif not want_flight and self.state == FLIGHT:
            self.enter(LANDING)
            response.success = True
            response.message = 'landing requested; watch /dogcopter/mode'
        else:
            response.success = False
            response.message = f'rejected: cannot switch from state {self.state}'
        return response

    # --- state machine ------------------------------------------------------

    def enter(self, state):
        self.get_logger().info(f'{self.state} -> {state}')
        if self.state == GROUND and state != GROUND:
            self.stop_wheels()
        self.state = state
        self.transition_elapsed = 0.0
        self.arm_retries = 0
        self.publish_mode()

    def publish_mode(self):
        self.mode_pub.publish(String(data=self.state))

    def on_timer(self):
        self.publish_mode()
        if self.state == TAKING_OFF:
            self.transition_elapsed += 1.0
            if self.arming_state != VehicleStatus.ARMING_STATE_ARMED:
                # Takeoff first, then arm: commander latches AUTO_TAKEOFF and
                # climbs to MIS_TAKEOFF_ALT as soon as arming succeeds.
                self.send_command(VehicleCommand.VEHICLE_CMD_NAV_TAKEOFF)
                self.send_command(
                    VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
                self.arm_retries += 1
                if self.arm_retries == ARM_RETRY_HINT_COUNT:
                    self.get_logger().warn(
                        'arming not confirmed yet — if headless, check '
                        "NAV_DLL_ACT (pxh: param set NAV_DLL_ACT 0) or connect QGC")
            elif (self.nav_state == VehicleStatus.NAVIGATION_STATE_AUTO_LOITER
                    and self.landed is False):
                self.enter(FLIGHT)
            if self.state == TAKING_OFF and self.transition_elapsed > TRANSITION_TIMEOUT_S:
                self.get_logger().error('takeoff timed out, reverting to GROUND')
                self.send_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
                self.enter(GROUND)
        elif self.state == LANDING:
            self.transition_elapsed += 1.0
            self.send_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
            if (self.landed is True
                    and self.arming_state == VehicleStatus.ARMING_STATE_DISARMED):
                self.enter(GROUND)
            elif self.transition_elapsed > TRANSITION_TIMEOUT_S:
                # Stay in LANDING (never re-enable wheels mid-air); keep retrying.
                self.get_logger().warn('landing not confirmed yet, still retrying')
                self.transition_elapsed = 0.0

    # --- PX4 commands ----------------------------------------------------------

    def send_command(self, command, param1=float('nan'), param2=float('nan')):
        msg = VehicleCommand()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        msg.command = command
        msg.param1 = param1
        msg.param2 = param2
        msg.param3 = float('nan')
        msg.param4 = float('nan')
        msg.param5 = float('nan')
        msg.param6 = float('nan')
        msg.param7 = float('nan')
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        self.vehicle_command_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ModeManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
