import os
from arm import Arm
import json

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")

robot = Arm()
robot.go_home()

positions = {}  # here we store {"name": [6 angles]}

# loop: record AS MANY positions as we want, not just 2
while True:
    name = input("Position name (empty Enter to finish): ")
    if name == "":
        break

    # the arm goes limp and we place it by hand
    robot.release_motors()
    input(f"Place the robot at '{name}' and press Enter...")

    # read the ANGLES (not coordinates) and store them with their name
    angles = robot.read_angles()
    positions[name] = angles
    print(f"Saved '{name}':", angles)

    # rigid again and back home before the next one
    robot.lock_motors()
    robot.go_home()

# write the whole dictionary to the JSON file
with open(FILE, "w") as file:
    json.dump(positions, file, indent=4)
print(f"{len(positions)} positions saved to {FILE}")
