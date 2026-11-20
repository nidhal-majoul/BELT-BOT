import serial  # pip install pyserial
import time


# class to control the conveyor belt from python
# python sends text commands to the arduino and the arduino moves the motor
class Conveyor:

    MIN_SPEED = 0
    MAX_SPEED = 255
    SPEED_STEP = 25  # how much the speed goes up/down each time

    def __init__(self, port="COM5", baudrate=9600):
        # open the port of the arduino (look the COM in arduino IDE -> tools -> port)
        self._serial = serial.Serial(port, baudrate, timeout=1)
        # when we open the port the arduino restarts, so we wait for READY
        self._wait_for_ready()
        # we save the state here too, it starts like the arduino
        self._running = False
        self._clockwise = True
        self._speed = 150

    def _wait_for_ready(self, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            line = self._serial.readline().decode(errors="ignore").strip()
            if line == "READY":
                return
        # if after 5 seconds nothing arrives, probably the COM is wrong
        raise RuntimeError("The Arduino did not answer READY. Check the COM port.")

    def _send(self, command):
        # we add "\n" because the arduino reads until the end of the line
        self._serial.write((command + "\n").encode())
        reply = self._serial.readline().decode(errors="ignore").strip()
        if reply.startswith("ERROR"):
            raise RuntimeError(f"Arduino error: {reply}")
        return reply

    def start(self):
        self._send("START")
        self._running = True

    def stop(self):
        self._send("STOP")
        self._running = False

    def clockwise(self):
        self._send("CW")
        self._clockwise = True

    def counter_clockwise(self):
        self._send("CCW")
        self._clockwise = False

    def set_speed(self, speed):
        # the speed can't be less than 0 or more than 255
        speed = max(self.MIN_SPEED, min(self.MAX_SPEED, speed))
        self._send(f"SPEED {speed}")
        self._speed = speed

    def speed_up(self):
        self.set_speed(self._speed + self.SPEED_STEP)

    def speed_down(self):
        self.set_speed(self._speed - self.SPEED_STEP)

    def is_running(self):
        return self._running

    def __str__(self):
        state = "ON" if self._running else "OFF"
        direction = "CW" if self._clockwise else "CCW"
        return f"Conveyor {state} | {direction} | speed {self._speed}"

    def close(self):
        # first we stop the belt, then we close the port
        try:
            self.stop()
        finally:
            self._serial.close()


if __name__ == "__main__":
    # small test without the camera: 3 sec one way, 3 sec the other way and stop
    conveyor = Conveyor("COM5")
    print(conveyor)
    conveyor.start()
    print(conveyor)
    time.sleep(3)
    conveyor.counter_clockwise()
    print(conveyor)
    time.sleep(3)
    conveyor.close()
    print("Closed")
