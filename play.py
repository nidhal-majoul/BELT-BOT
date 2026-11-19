from arm import Arm
import json

FILE = "positions.json"

# read the positions saved by record.py
with open(FILE, "r") as file:
    positions = json.load(file)
print("Positions loaded:", list(positions.keys()))

robot = Arm()
input("NOW THE ROBOT PLAYS ON ITS OWN (press Enter)")


for name, angles in positions.items():
    print("Going to:", name)
    robot.move_angles(angles)

robot.go_home()
print("ALL DONE")