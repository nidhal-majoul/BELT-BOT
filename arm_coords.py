from arm import Arm
import time


class ArmCoords(Arm):
    """Inherits EVERYTHING from Arm (angles, release, lock, go_home...)
    and adds control by coordinates (x, y, z, rx, ry, rz).
    We no longer use it to record/play, but we keep it in case
    we ever need to move the robot to a specific point in space."""

    def read_coords(self):
        # returns [x, y, z, rx, ry, rz] of the robot tip
        return self._mc.get_coords()

    def move_coords(self, coords, speed=15):
        # the last 0 = normal movement mode (not a straight line)
        self._mc.send_coords(coords, speed, 0)
        time.sleep(8)

    # go_home() is not needed here anymore: it is inherited from Arm
    
