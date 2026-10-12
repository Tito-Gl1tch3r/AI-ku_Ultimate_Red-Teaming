# /modules/pb_scrape_keywords.py
import requests
from modules.base import BaseModule
from pathlib import Path
from core.utils.formatter import printc, colorize
from rich.text import Text


def normalize_url(u):
    if not u.startswith("http://") and not u.startswith("https://"):
        return "https://" + u
    return u


class Module(BaseModule):
    def __init__(self):
        super().__init__()

        self.name = "pb_scrape_keywords"
        self.description = (
            "Scrapes single or multiple web pages "
            "to detect specific keywords in raw HTML content."
        )
        self.category = "utility"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = "https://github.com/bkili"
        self.license = ""
        self.version = "0.0.1"

        # Default options for the module
        self.default_options = {"url": "", "input_file": "", "keywords": ""}

        # List of options that are considered required
        # (shown in CLI with 'yes' under Required)
        self.required_options = ["url", "keywords"]

        self.options = self.default_options.copy()

    def requires(self):
        return []

    def run(self, shared_data):
        # Options
        url = self.options.get("url", "").strip()
        input_file = self.options.get("input_file", "").strip()
        keywords_raw = self.options.get("keywords", "").strip()
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

        if url and input_file:
            printc(
                "Error: Provide either 'url' or 'input_file', not both.", level="error"
            )
            return
        if not url and not input_file:
            printc(
                "Error: You must provide either 'url' or 'input_file'.", level="error"
            )
            return
        if not keywords:
            printc("Error: No keywords provided.", level="error")
            return

        urls = []
        if input_file:
            input_path = Path(input_file)
            if not input_path.exists():
                printc(f"Error: File {input_file} not found.", level="error")
                return
            with open(input_path, "r") as f:
                urls = [normalize_url(line.strip()) for line in f if line.strip()]
        else:
            urls = [normalize_url(url)]

        for u in urls:
            try:
                resp = requests.get(u, timeout=10)
                lines = resp.text.splitlines()
                matches_found = False
                for line in lines:
                    for keyword in keywords:
                        if keyword in line.lower():
                            msg = (
                                Text("[+] ")
                                + colorize(u, "cyan")
                                + Text(" contains ")
                                + colorize(keyword, "green", "bold")
                            )
                            printc(msg)
                            printc("  " + line.strip(), level="info")
                            matches_found = True
                            break
                if not matches_found:
                    printc(f"[-] No match found in {u}", level="warn")
            except Exception as e:
                printc(f"[!] Error processing {u}: {e}", level="error")
