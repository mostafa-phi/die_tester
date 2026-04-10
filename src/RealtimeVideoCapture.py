import threading
import queue as Queue
import cv2 as cv
import time
import numpy as np

# https://stackoverflow.com/a/69141497
# Video capture that saves latest frame to a buffer, for realtime image return. (Temporary workaround; was unable to compile opencv with gstreamer for native realtime video compatibility.)
class RealtimeVideoCapture:
    def __init__(self, name, resolution=(1920.0, 1080.0)):
        self.cap = cv.VideoCapture(name)
        if not self.cap.isOpened():
            raise ConnectionError("Cannot open camera.")

        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, resolution[1])

        self.q = Queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()   # discard previous (unprocessed) frame
                except Queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        return self.q.get()
  
    def mean_capture(self, num_images, pause_time=1/30, convert_to_grayscale=True): # capture multiple images to reduce noise.
        img_list = []
        for _ in range(num_images):
            img = self.read()
            if convert_to_grayscale:
                img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)  # Convert BGR -> Grayscale
                img_list.append(img)
            else:
                img = cv.cvtColor(img, cv.COLOR_BGR2RGB)  # Convert BGR -> RGB
                img_list.append(img)
            time.sleep(pause_time)

        return np.mean(np.asarray(img_list), axis=0).astype(np.uint8)