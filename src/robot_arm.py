from abc import ABC, abstractmethod


# abstract class for any robot arm: the real myCobot and the virtual one
# the interface only talks to this class, so it doesn't care if the robot is
# real or simulated -> polymorphism (Strategy pattern)
class RobotArm(ABC):

    HOME_POSITION = [0, 0, 0, 0, 0, 0]  # arm straight up

    @abstractmethod
    def read_angles(self):
        # returns the 6 angles in degrees
        pass

    @abstractmethod
    def move_angles(self, angles, speed=30):
        # moves the 6 joints and waits until the arm arrives
        pass

    @abstractmethod
    def open_gripper(self, opening=50, speed=50):
        pass

    @abstractmethod
    def close_gripper(self, speed=50):
        pass

    @abstractmethod
    def release_motors(self):
        # the arm goes limp (only makes sense in the real robot)
        pass

    @abstractmethod
    def lock_motors(self):
        pass

    @abstractmethod
    def close(self):
        # free the connection / the simulation
        pass

    def go_home(self):
        # the same for every robot, so it's written only once here
        self.move_angles(self.HOME_POSITION, 20)
