import json
import os

# positions.json is next to this file, so it works from any folder
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")


# saves and loads the positions of the robot {"name": [6 angles]}
# the same file is used by the real and the virtual robot
class PositionManager:

    def __init__(self, file=DEFAULT_FILE):
        self._file = file
        self._positions = {}

    def load(self):
        if os.path.exists(self._file):
            with open(self._file, "r") as f:
                self._positions = json.load(f)
        return self

    def save(self):
        with open(self._file, "w") as f:
            json.dump(self._positions, f, indent=4)

    def add(self, name, angles):
        # if the name already exists we overwrite it
        self._positions[name] = [round(float(a), 2) for a in angles]
        self.save()

    def delete(self, name):
        if name in self._positions:
            del self._positions[name]
            self.save()

    def get(self, name):
        return self._positions[name]

    def names(self):
        # in the same order they were recorded
        return list(self._positions.keys())
