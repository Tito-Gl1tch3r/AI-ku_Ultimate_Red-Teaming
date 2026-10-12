import os
import sys
import plistlib
from ..utils import run_command

class Startup:
    def __init__(self, env):
        self.env_launch_agent_label = env.ENV_LAUNCH_AGENT_LABEL
        self.env_launch_agent_dir = env.ENV_LAUNCH_AGENT_DIR
        self.env_plist_path = env.ENV_PLIST_PATH
        self.env_curr_project_dir = env.ENV_CURR_PROJECT_DIR

    def write_launch_agent(self):
        print(f"Creating LaunchAgent plist at {self.env_plist_path} ...")
        os.makedirs(self.env_launch_agent_dir, exist_ok=True)

        if getattr(sys, 'frozen', False):
            # Compiled with PyInstaller
            executable_path = os.path.realpath(sys.executable)
            program_args = [executable_path, "--intercept-on"]
        else:
            # Running as plain Python
            python_executable = sys.executable
            script_path = os.path.realpath('main.py')
            program_args = [python_executable, script_path, "--intercept-on"]

        plist = {
            "Label": self.env_launch_agent_label,
            "ProgramArguments": program_args,
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": os.path.join(self.env_curr_project_dir, "agent.log"),
            "StandardErrorPath": os.path.join(self.env_curr_project_dir, "agent.err"),
            "WorkingDirectory": self.env_curr_project_dir
        }

        with open(self.env_plist_path, "wb") as f:
            plistlib.dump(plist, f)

        # Set correct permissions
        os.chown(self.env_plist_path, 0, 0)  # root:wheel
        os.chmod(self.env_plist_path, 0o644)

        # Reload daemon
        run_command(["launchctl", "unload", self.env_plist_path], sudo=True)
        run_command(["launchctl", "load", self.env_plist_path], sudo=True)

        print(f"LaunchAgent {self.env_launch_agent_label} installed and loaded.")



    def unload_and_remove_launch_agent(self):
        print("Unloading and removing launch agent...")
        if os.path.exists(self.env_plist_path):
            run_command(["launchctl", "unload", self.env_plist_path], sudo=False)
            os.remove(self.env_plist_path)
            print(f"Removed launch agent plist: {self.env_plist_path}")
        else:
            print("Launch agent plist not found; skipping removal.")