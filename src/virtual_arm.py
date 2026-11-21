import os
import time
import numpy as np
import mujoco
from robot_arm import RobotArm

# the 3D model of the myCobot 280 (made from the official Elephant Robotics model)
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "models", "mycobot280", "mycobot280.xml")


# the VIRTUAL myCobot: same methods as the real one, but it moves in MuJoCo
class VirtualArm(RobotArm):

    FINGER_MAX = 0.018   # how much each finger can open (metres)
    DEG_PER_SPEED = 2.0  # speed 30 -> 60 degrees per second, more or less like the real one
    FPS = 30             # images we send to the interface per second
    PIECE_HALF = 0.0225  # the piece is a 4.5 cm cube
    BELT_START_X = -0.48 # where a new piece appears on the belt
    BELT_Y = 0.015
    BELT_TOP = -0.003    # height of the belt surface
    BOX_CENTER = (-0.10, 0.25)
    BOX_HALF = (0.085, 0.065)
    BOX_FLOOR = -0.026
    BELT_SPEED = 0.08    # metres per second

    def __init__(self, on_state=None):
        self._model = mujoco.MjModel.from_xml_path(MODEL_PATH)
        self._data = mujoco.MjData(self._model)
        # function that receives the state of the arm (joint positions) to draw it
        self._on_state = on_state
        self._tcp = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_SITE, "tcp")
        piece_body = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, "piece")
        self._piece = self._model.body_mocapid[piece_body]
        self.piece_state = "hidden"    # hidden / on_belt / held / in_box / dropped
        mujoco.mj_forward(self._model, self._data)

    # ---------- small helpers ----------
    def _render(self):
        # we don't draw here: we send a copy of the joints to the window,
        # and the window draws it (OpenGL works better in the main thread)
        if self._on_state is not None:
            self._on_state((self._data.qpos.copy(), self._data.mocap_pos.copy()))

    def _simulate(self, seconds, ctrl_from=None, ctrl_to=None):
        # runs the physics for some seconds, moving the targets little by little
        steps = max(1, int(seconds / self._model.opt.timestep))
        steps_per_frame = max(1, int(1 / (self.FPS * self._model.opt.timestep)))
        start = time.perf_counter()
        for i in range(steps):
            if ctrl_from is not None:
                k = (i + 1) / steps
                self._data.ctrl[:] = ctrl_from + (ctrl_to - ctrl_from) * k
            mujoco.mj_step(self._model, self._data)
            if self.piece_state == "held":
                # the piece goes with the gripper
                self._data.mocap_pos[self._piece] = self._data.site_xpos[self._tcp]
            if i % steps_per_frame == 0:
                self._render()
                # we wait so the virtual robot moves in real time, not super fast
                wait = (i + 1) * self._model.opt.timestep - (time.perf_counter() - start)
                if wait > 0:
                    time.sleep(wait)

    # ---------- RobotArm methods ----------
    def read_angles(self):
        return [round(float(a), 2) for a in np.degrees(self._data.qpos[:6])]

    def move_angles(self, angles, speed=30):
        start = self._data.ctrl.copy()
        target = start.copy()
        target[:6] = np.radians(angles)
        biggest = float(np.max(np.abs(np.degrees(target[:6] - start[:6]))))
        seconds = max(0.3, biggest / (speed * self.DEG_PER_SPEED))
        self._simulate(seconds, start, target)
        self._simulate(0.3)  # a moment to settle, like the real robot

    def open_gripper(self, opening=50, speed=50):
        start = self._data.ctrl.copy()
        target = start.copy()
        target[6:8] = self.FINGER_MAX * opening / 100
        self._simulate(0.6, start, target)
        if self.piece_state == "held":
            self._drop_piece()

    def close_gripper(self, speed=50):
        start = self._data.ctrl.copy()
        target = start.copy()
        target[6:8] = 0.0
        self._simulate(0.6, start, target)
        # if the piece is between the fingers, now we have it
        distance = np.linalg.norm(self._data.site_xpos[self._tcp] - self._data.mocap_pos[self._piece])
        if self.piece_state == "on_belt" and distance < 0.05:
            self.piece_state = "held"

    def release_motors(self):
        pass  # in the simulation we move the arm with the sliders, not by hand

    def lock_motors(self):
        pass

    def close(self):
        pass  # nothing to free, the drawing is done by ArmView

    # ---------- the piece (only in the simulation) ----------
    def _move_piece(self, start, end, seconds):
        # moves the piece in a straight line (the belt moving it, or the piece falling)
        frames = max(1, int(seconds * self.FPS))
        for i in range(1, frames + 1):
            self._data.mocap_pos[self._piece] = start + (end - start) * i / frames
            mujoco.mj_forward(self._model, self._data)
            self._render()
            time.sleep(1 / self.FPS)

    def tcp_for(self, angles):
        # where the gripper would be with these angles (without moving the robot)
        data = mujoco.MjData(self._model)
        data.qpos[:6] = np.radians(angles)
        mujoco.mj_forward(self._model, data)
        return data.site_xpos[self._tcp].copy()

    def run_belt(self, detected, extra_time=0.3, timeout=12):
        # a new piece comes on the belt and keeps moving until the camera
        # detects it (the window sets the event "detected"), like the real cell
        z = self.BELT_TOP + self.PIECE_HALF
        pos = np.array([self.BELT_START_X, self.BELT_Y, z])
        self.piece_state = "on_belt"
        dt = 1 / self.FPS
        stop_at = None
        t = 0.0
        while t < timeout:
            if stop_at is None and detected.is_set():
                stop_at = t + extra_time      # the push: a bit more and then stop
            if stop_at is not None and t >= stop_at:
                return True
            pos[0] += self.BELT_SPEED * dt
            if pos[0] > -0.18:                # end of the belt
                return False
            self._data.mocap_pos[self._piece] = pos
            mujoco.mj_forward(self._model, self._data)
            self._render()
            time.sleep(dt)
            t += dt
        return False

    def place_piece_at_start(self):
        z = self.BELT_TOP + self.PIECE_HALF
        self._data.mocap_pos[self._piece] = [self.BELT_START_X, self.BELT_Y, z]
        self.piece_state = "on_belt"
        mujoco.mj_forward(self._model, self._data)
        self._render()

    def new_piece(self, stop_x=-0.255, seconds=2.5):
        # a new piece comes on the belt and stops where the robot picks it
        z = self.BELT_TOP + self.PIECE_HALF
        start = np.array([self.BELT_START_X, self.BELT_Y, z])
        end = np.array([stop_x, self.BELT_Y, z])
        self.piece_state = "on_belt"
        self._data.mocap_pos[self._piece] = start
        self._move_piece(start, end, seconds)

    def _drop_piece(self):
        pos = self._data.mocap_pos[self._piece].copy()
        cx, cy = self.BOX_CENTER
        hx, hy = self.BOX_HALF
        in_box = abs(pos[0] - cx) < hx and abs(pos[1] - cy) < hy
        floor = self.BOX_FLOOR if in_box else -0.03
        end = np.array([pos[0], pos[1], floor + self.PIECE_HALF])
        self.piece_state = "in_box" if in_box else "dropped"
        self._move_piece(pos, end, 0.3)

    # ---------- extra: show some angles without physics ----------
    def show_angles(self, angles):
        # puts the arm directly in these angles (used to copy the real robot)
        self._data.qpos[:6] = np.radians(angles)
        self._data.ctrl[:6] = np.radians(angles)
        self._data.qvel[:] = 0
        mujoco.mj_forward(self._model, self._data)
        self._render()


# draws the virtual arm into an image. It has its own copy of the model,
# so it can draw in the window thread while VirtualArm moves in the robot thread
class ArmView:

    def __init__(self, width=640, height=480, camera="front", cam_size=(320, 240)):
        self._model = mujoco.MjModel.from_xml_path(MODEL_PATH)
        self._data = mujoco.MjData(self._model)
        self._renderer = mujoco.Renderer(self._model, height, width)
        self._cam_renderer = mujoco.Renderer(self._model, cam_size[1], cam_size[0])
        self._camera = camera
        self.cam_size = cam_size
        cam_id = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_CAMERA, "belt_cam")
        self.cam_pos = self._model.cam_pos[cam_id].copy()
        self.cam_fovy = float(self._model.cam_fovy[cam_id])

    def draw(self, state):
        qpos, mocap_pos = state
        self._data.qpos[:] = qpos
        self._data.mocap_pos[:] = mocap_pos
        mujoco.mj_forward(self._model, self._data)   # only the geometry, no physics
        self._renderer.update_scene(self._data, camera=self._camera)
        return self._renderer.render()               # RGB image

    def draw_camera(self):
        # what the camera over the belt sees (uses the state of the last draw)
        self._cam_renderer.update_scene(self._data, camera="belt_cam")
        return self._cam_renderer.render()

    def tcp_for(self, angles):
        data = mujoco.MjData(self._model)
        data.qpos[:6] = np.radians(angles)
        mujoco.mj_forward(self._model, data)
        tcp = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_SITE, "tcp")
        return data.site_xpos[tcp].copy()

    def close(self):
        self._renderer.close()
        self._cam_renderer.close()
