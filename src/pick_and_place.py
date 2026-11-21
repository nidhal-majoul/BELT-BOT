import os
import cv2
import json
import time
from arm import Arm
from conveyor import Conveyor
from piece_detector import PieceDetector

# settings -> copy here the values that worked in conveyor_camera.py
ARM_PORT = "COM4"
CONVEYOR_PORT = "COM3"
CAMERA_INDEX = 1
ROI = (300, 100, 120, 220)
# positions.json is next to this file, so it works from any folder
POSITIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")
# seconds the belt keeps moving after the camera sees the piece
# (the push, so the piece goes more to the centre and the robot catches it well)
# if the piece stops too early -> bigger number, if it goes too far -> smaller
EXTRA_TIME = 0.4

# names of the positions we need
NEEDED = ["above_pick", "pick", "above_box", "box"]


def load_positions():
    with open(POSITIONS_FILE, "r") as file:
        positions = json.load(file)
    # check that we recorded all the positions we need
    missing = [name for name in NEEDED if name not in positions]
    if missing:
        raise RuntimeError(f"Missing positions {missing}. Record them with record.py")
    return positions


def pick_and_place(arm, p):
    # the whole movement of the robot, step by step
    arm.open_gripper()
    arm.move_angles(p["above_pick"])  # first above the piece, so we don't hit it
    arm.move_angles(p["pick"])        # go down
    arm.close_gripper()               # catch it
    arm.move_angles(p["above_pick"])  # go up with the piece
    arm.move_angles(p["above_box"])
    arm.move_angles(p["box"])
    arm.open_gripper()                # drop it in the box
    arm.move_angles(p["above_box"])
    # if we recorded a "home" we use it, if not the arm goes straight up
    if "home" in p:
        arm.move_angles(p["home"])
    else:
        arm.go_home()


positions = load_positions()
arm = Arm(ARM_PORT)
conveyor = Conveyor(CONVEYOR_PORT)
detector = PieceDetector(CAMERA_INDEX, ROI)

try:
    arm.go_home()
    input("Make sure the belt is EMPTY and press Enter to calibrate...")
    detector.calibrate()
    print("Calibrated. q = quit")

    conveyor.start()
    armed = False  # same idea as in conveyor_camera.py

    while True:
        frame = detector.read_frame()
        present = detector.piece_present(frame)

        if not present:
            armed = True
        elif armed and conveyor.is_running():
            # the piece just entered the zone, we let the belt move a little more
            time.sleep(EXTRA_TIME)
            conveyor.stop()
            armed = False
            print("Piece detected -> robot picks it")
            pick_and_place(arm, positions)
            # while the robot was moving the camera saved old frames,
            # so we throw some away to see the real image again
            for _ in range(5):
                detector.read_frame()
            conveyor.start()
            print("Piece in the box -> belt started again")

        detector.draw(frame, present)
        cv2.imshow("Pick and place", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    # always stop everything, also if there is an error
    conveyor.close()
    detector.close()
    print("Closed")