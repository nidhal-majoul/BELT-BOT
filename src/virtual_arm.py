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

    def __init__(self, on_state=None):
        self._model = mujoco.MjModel.from_xml_path(MODEL_PATH)
        self._data = mujoco.MjData(self._model)
        # function that receives the state of the arm (joint positions) to draw it
        self._on_state = on_state
        mujoco.mj_forward(self._model, self._data)

    # ---------- small helpers ----------
    def _render(self):
        # we don't draw here: we send a copy of the joints to the window,
        # and the window draws it (OpenGL works better in the main thread)
        if self._on_state is not None:
            self._on_state(self._data.qpos.copy())

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

    def close_gripper(self, speed=50):
        start = self._data.ctrl.copy()
        target = start.copy()
        target[6:8] = 0.0
        self._simulate(0.6, start, target)

    def release_motors(self):
        pass  # in the simulation we move the arm with the sliders, not by hand

    def lock_motors(self):
        pass

    def close(self):
        pass  # nothing to free, the drawing is done by ArmView

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

    def __init__(self, width=640, height=480, camera="front"):
        self._model = mujoco.MjModel.from_xml_path(MODEL_PATH)
        self._data = mujoco.MjData(self._model)
        self._renderer = mujoco.Renderer(self._model, height, width)
        self._camera = camera

    def draw(self, qpos):
        self._data.qpos[:] = qpos
        mujoco.mj_forward(self._model, self._data)   # only the geometry, no physics
        self._renderer.update_scene(self._data, camera=self._camera)
        return self._renderer.render()               # RGB image

    def close(self):
        self._renderer.close()
