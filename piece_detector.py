import cv2 


# class to know if there is a piece in one zone of the camera image
class PieceDetector:

    def __init__(self, camera_index, roi, threshold=0.23):
        self._camera = cv2.VideoCapture(camera_index)
        if not self._camera.isOpened():
            raise RuntimeError(f"Could not open camera {camera_index}")
        self._roi = roi              # the zone (x, y, w, h) in pixels
        self._threshold = threshold  # 0.15 = if more than 15% changes we say piece
        self._reference = None       # photo of the empty zone
        self.last_change = 0.0       

    def read_frame(self):
        ok, frame = self._camera.read()
        if not ok:
            raise RuntimeError("Could not read a frame from the camera")
        return frame

    def _crop_gray(self, frame):
        # we cut only the zone
        x, y, w, h = self._roi
        zone = frame[y:y + h, x:x + w]
        gray = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (5, 5), 0)

    def calibrate(self):
        # the belt has to be empty here
        for _ in range(10):
            frame = self.read_frame()
        self._reference = self._crop_gray(frame)

    def piece_present(self, frame):
        if self._reference is None:
            raise RuntimeError("Call calibrate() first")
        zone = self._crop_gray(frame)
        diff = cv2.absdiff(self._reference, zone)  # difference pixel by pixel
        # pixels that changed more than 40 -> white, the rest -> black
        _, mask = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
        x, y, w, h = self._roi
        self.last_change = cv2.countNonZero(mask) / (w * h)  # % of white pixels
        return self.last_change > self._threshold

    def draw(self, frame, present):
        # rectangle of the zone: green if it's empty, red if there is a piece
        x, y, w, h = self._roi
        color = (0, 0, 255) if present else (0, 255, 0)  # opencv uses BGR not RGB
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        text = f"change {self.last_change:.0%}"
        cv2.putText(frame, text, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def close(self):
        self._camera.release()
        cv2.destroyAllWindows()
