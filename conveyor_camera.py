import cv2
from conveyor import Conveyor
from piece_detector import PieceDetector

# settings, change them for your setup
CONVEYOR_PORT = "COM5"       # port of the arduino (the robot is in another COM)
CAMERA_INDEX = 1             # 0 is the laptop webcam, 1 should be the belt camera
ROI = (300, 200, 120, 120)   # x, y, w, h -> the zone where the piece has to stop

conveyor = Conveyor(CONVEYOR_PORT)
detector = PieceDetector(CAMERA_INDEX, ROI)

try:
    input("Make sure the belt is EMPTY and press Enter to calibrate...")
    detector.calibrate()
    print("Calibrated. Keys: s = start belt, c = recalibrate, q = quit")

    conveyor.start()
    # armed: we only stop if the zone was empty before
    # without this, when we start again the piece is still there and it stops again
    armed = False

    while True:
        frame = detector.read_frame()
        present = detector.piece_present(frame)

        if not present:
            armed = True  # zone empty, ready for the next piece
        elif armed and conveyor.is_running():
            conveyor.stop()
            armed = False
            print("Piece detected -> belt stopped")

        detector.draw(frame, present)
        cv2.imshow("Conveyor camera", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            conveyor.start()
            print("Belt started")
        elif key == ord("c"):
            conveyor.stop()
            input("Empty the belt and press Enter...")
            detector.calibrate()
            print("Recalibrated")

finally:
    # this always runs, also if there is an error, so the belt never stays on
    conveyor.close()
    detector.close()
    print("Closed")
