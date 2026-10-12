import argparse
import logging
import os
import subprocess  # nosec
from typing import List

from powerpwn.copilot_studio.modules.path_utils import get_project_file_path


def query_tools_using_pup(bot_urls: List[str]) -> None:
    """
    Execute the Puppeteer JavaScript code for each bot URL given.
    The function calls a different JavaScript file.
    :param bot_urls: The list of bot URLs needed to check
    """
    pup_path = get_project_file_path("tools/pup_query_webchat", "query_chat_tools.js")
    output_path = get_project_file_path("final_results/", "chat_exists_output_tools.xlsx")

    # Delete the existing Excel file to start fresh
    if os.path.exists(output_path):
        os.remove(output_path)
        logging.debug(f"Deleted existing file: {output_path}")

    for bot_url in bot_urls:
        try:
            # Construct the shell command
            command = f"node {pup_path} '{bot_url}'"
            logging.debug(f"Running command: `{command}`")
            # Run the command
            subprocess.run(command, shell=True, check=True)  # nosec
        except subprocess.CalledProcessError as e:
            logging.error(f"Error occurred while running Puppeteer: {e}")

    if os.path.exists(output_path):
        print(f"Done, recon tools results saved under {output_path}")
    else:
        print("No results were generated.")


class ToolsRecon:
    """
    A class that is responsible for the CPS tools recon
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.urls: List[str] = []
        self.run()

    def run(self) -> None:
        if self.args.url:
            self.urls.append(self.args.url)
        elif self.args.input_file:
            if not os.path.exists(self.args.input_file):
                logging.error(f"Input file not found: {self.args.input_file}")
                return
            with open(self.args.input_file, "r") as f:
                self.urls = [line.strip() for line in f if line.strip()]

        if not self.urls:
            logging.error("No URLs to process. Please provide a URL or an input file.")
            return

        print(f"Starting tools reconnaissance on {len(self.urls)} URL(s).")
        query_tools_using_pup(self.urls)
