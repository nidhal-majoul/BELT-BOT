from pymycobot import MyCobot280
import time  # for pauses (sleep)


class Arm:
    """REAL myCobot robot. Everything works with the ANGLES of the 6 joints,
    so the same JSON file can later be used by the virtual robot."""

    HOME_POSITION = [0, 0, 0, 0, 0, 0]  # arm straight up

    def __init__(self, port="COM4", baudrate=115200):
        # connect to the robot through the COM port
        self._mc = MyCobot280(port, baudrate)
        # give the connection one second to settle
        time.sleep(1)

    def read_angles(self):
        # sometimes the robot does not answer the first time and returns -1
        # or an empty list, so we retry a few times before raising an error
        for _ in range(5):
            angles = self._mc.get_angles()
            if isinstance(angles, list) and len(angles) == 6:
                return angles
            time.sleep(0.2)
        raise RuntimeError("Could not read the robot angles")

    def move_angles(self, angles, speed=30):
        # moves all 6 joints at once and WAITS until the robot arrives.
        # if your pymycobot version has sync_send_angles, we use it (it waits by itself);
        # otherwise we send the normal command and wait a fixed time
        if hasattr(self._mc, "sync_send_angles"):
            self._mc.sync_send_angles(angles, speed, timeout=15)
        else:
            self._mc.send_angles(angles, speed)
            time.sleep(5)

    def move_joint(self, joint, angle, speed=20):
        # moves ONE single joint (1 = base ... 6 = wrist)
        self._mc.send_angle(joint, angle, speed)
        time.sleep(4)

    def go_home(self):
        # puts the arm straight (defined here so every arm class inherits it)
        self.move_angles(self.HOME_POSITION, 20)

    def release_motors(self):
        # the arm goes limp so you can move it by hand
        self._mc.release_all_servos()

    def lock_motors(self):
        # the arm becomes rigid again
        self._mc.power_on()
        time.sleep(2)


if __name__ == "__main__":
    # quick test: read, turn the base and come back
    robot = Arm()
    print("Angles:", robot.read_angles())
    robot.move_joint(1, 90)  # joint 1 = base, turn it to 90 degrees
    print("After turning:", robot.read_angles())
    robot.move_joint(1, 0)   # back to 0 degrees
    print("After returning:", robot.read_angles())

