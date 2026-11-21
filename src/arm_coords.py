from arm import Arm
import time


class ArmCoords(Arm):
    
    def read_coords(self):
        # returns [x, y, z, rx, ry, rz] 
        return self._mc.get_coords()

    def move_coords(self, coords, speed=15):
        self._mc.send_coords(coords, speed, 0)
        time.sleep(8)

    
