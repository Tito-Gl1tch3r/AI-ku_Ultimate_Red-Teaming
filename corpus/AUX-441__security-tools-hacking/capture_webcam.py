import cv2
import time
import random
from datetime import datetime
import os


# 8/13/2025
# Get JPG Picture from user Face if camera enabled
# AUX-441


class Camera_:
    def get_picture(self, save_path="captured_faces"):
        os.makedirs(save_path, exist_ok=True)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Cannot access camera")
            return None

        print("Camera activated.")
        time.sleep(random.randint(1,3))

        ret, frame = cap.read()
        if not ret:
            print("Failed to capture image")
            cap.release()
            return None

        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        full_path = os.path.join(save_path, filename)

        cv2.imwrite(full_path, frame)
        cap.release()
        print(f"Picture saved to {full_path}")
        return full_path


if __name__ == "__main__":
    cam = Camera_()
    cam.get_picture()

