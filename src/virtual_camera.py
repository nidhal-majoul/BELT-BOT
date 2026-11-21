import numpy as np
from piece_detector import PieceDetector


# the same detector we use with the real camera, but the images come from
# the camera of the simulation instead of a USB camera (inheritance)
class VirtualPieceDetector(PieceDetector):

    def __init__(self, roi=(0, 0, 10, 10), threshold=0.15):
        # we don't call super().__init__ because it would open a real camera
        self._roi = roi
        self._threshold = threshold
        self._reference = None
        self.last_change = 0.0
        self._frame = None

    def set_roi(self, roi):
        self._roi = roi

    def give_frame(self, frame):
        # the window gives us the last image of the virtual camera
        self._frame = frame

    def read_frame(self):
        return self._frame

    def close(self):
        pass


def world_to_pixel(point, cam_pos, fovy_deg, width, height):
    # camera looking straight down: x of the image = x of the world, y of the image = -y of the world
    f = (height / 2) / np.tan(np.radians(fovy_deg) / 2)
    depth = cam_pos[2] - point[2]
    u = width / 2 + (point[0] - cam_pos[0]) * f / depth
    v = height / 2 - (point[1] - cam_pos[1]) * f / depth
    return int(round(u)), int(round(v))
