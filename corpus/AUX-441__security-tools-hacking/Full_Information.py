import time
import random
import subprocess
from datetime import datetime
import os

# full_information from Target PC
# 8/13/2025
# AUX-441


class information:
    def information_(self):

        list_of_cmmnds = [
            "dir",
            "tasklist",
            "net user",
            "netstat /a",
            "ipconfig/all",
            "systeminfo",
            "arp -a",
            "route print",
            "driverquery",
            "sc query state= all",
            "net share",
            "schtasks /query /fo LIST /v",
            "wmic cpu get name,numberofcores,currentclockspeed",
            "wmic os get caption,version,osarchitecture,serialnumber",
            "qwinsta"
        ]
        time.sleep(random.randint(1,3))

        output_all = ""

        for i in list_of_cmmnds:
            try:
                print(f"Running command: {i}")
                run = subprocess.run(i,shell=True)
                output_all += f"\n\nCommand: {i}\nOutput:\n{run.stdout}\n\n{'-' * 50}\n\n"
                print(f"Succesfully Executed all commands : {run.stdout}")
            except Exception as e:
                print(f"Failed to execute commands : {e}")

        try:
            folder = "full_informations"
            if os.path.exists(folder):
                print("Folder already exist ....")
            else:
                os.makedirs(folder)

            path = "information.txt"
            full = os.path.join("full_informations",path)

            with open(full,"w",encoding="utf-8") as w:
                w.write(output_all)
            print(f"Succesfully Write all content to :{full}")

        except FileNotFoundError as f:
            print(f"Failed to Found Path : {f}")


if __name__ == "__main__":
    C = information()
    C.information_()



