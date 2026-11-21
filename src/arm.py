from pymycobot import MyCobot280
import time  # for pauses (sleep)
from robot_arm import RobotArm


# the REAL myCobot, it follows the same rules as the virtual one (RobotArm)
class Arm(RobotArm):

    def __init__(self, port="COM4", baudrate=115200):
        # connect to the robot through the COM port
        self._mc = MyCobot280(port, baudrate)
        # give the connection one second to settle
        time.sleep(1)

    def read_angles(self):
        # or an empty list, so we retry a few times before raising an error
        for _ in range(5):
            angles = self._mc.get_angles()
            if isinstance(angles, list) and len(angles) == 6:
                return angles
            time.sleep(0.2)
        raise RuntimeError("Could not read the robot angles")

    def move_angles(self, angles, speed=30):
        if hasattr(self._mc, "sync_send_angles"):
            self._mc.sync_send_angles(angles, speed, timeout=15)
        else:
            self._mc.send_angles(angles, speed)
            time.sleep(5)

    def move_joint(self, joint, angle, speed=20):
        self._mc.send_angle(joint, angle, speed)
        time.sleep(4)

    def release_motors(self):
        # the arm goes limp so we can move it by hand
        self._mc.release_all_servos()

    def lock_motors(self):
        # the arm becomes rigid again
        self._mc.power_on()
        time.sleep(2)

    def open_gripper(self,opening=50, speed=50):
        # 0 = open the gripper
        self._mc.set_gripper_value(opening, speed)
        time.sleep(1.5)  # we wait so the gripper finishes

    def close_gripper(self, speed=50):
        # 1 = close the gripper (to catch the piece)
        self._mc.set_gripper_state(1, speed)
        time.sleep(1.5)

    def close(self):
        # close the port so we can connect again later without restarting
        if hasattr(self._mc, "close"):
            self._mc.close()
        else:
            self._mc._serial_port.close()


if __name__ == "__main__":
    robot = Arm()
    print("Angles:", robot.read_angles())
    robot.move_joint(1, 90)  # joint 1 = base, turn it to 90 degrees
    print("After turning:", robot.read_angles())
    robot.move_joint(1, 0)   # back to 0 degrees
    print("After returning:", robot.read_angles())

