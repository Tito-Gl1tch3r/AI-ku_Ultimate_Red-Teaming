# /modules/pb_screenshot.py
import threading
import logging
import hashlib
from modules.base import BaseModule
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from core.utils.formatter import printc, colorize
from rich.text import Text


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


class Module(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "pb_screenshot"
        self.description = (
            "Takes screenshots of given or previously discovered URLs and saves them."
        )
        self.category = "utility"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = "https://github.com/bkili"
        self.license = ""
        self.version = "0.0.1"
        self.default_options = {
            "url": "",
            "headless": "true",
            "input_file": "",
            "output_directory": "screenshots",
            "retry_count": "2",
            "thread_count": "4",
            "page_load_timeout": 30,
            "wayback": "False",
        }
        self.required_options = [
            "headless",
            "input_file",
            "output_directory",
            "retry_count",
            "thread_count",
            "page_load_timeout",
        ]
        self.options = self.default_options.copy()

    def requires(self):
        url = self.options.get("url", "").strip()
        input_file = self.options.get("input_file", "").strip()
        wayback = self.options.get("wayback").lower()
        if (
            url
            and (not input_file or not Path(input_file).exists())
            and (wayback == "true")
        ):
            return ["pb_wayback"]
        return []

    def run(self, shared_data):
        printc(
            f"[{self.name}] Starting screenshot module...",
            level="module",
            use_tqdm=True,
        )
        logging.info(f"[{self.name}] Screenshot module started.")

        url_provided = self.options.get("url", "").strip() != ""
        input_file_path = self.options.get("input_file", "").strip()
        input_file_provided = input_file_path != ""

        wayback = self.options.get("wayback", False)

        if url_provided and input_file_provided:
            printc(
                f"[{self.name}] Error: Both 'url' and 'input_file' are set."
                "Please use only one.",
                level="error",
                use_tqdm=True,
            )
            return

        if not url_provided and not input_file_provided:
            printc(
                f"[{self.name}] Error: Neither 'url' nor 'input_file' is provided.",
                level="error",
                use_tqdm=True,
            )
            return

        urls = []

        if input_file_provided:
            input_path = Path(input_file_path)
            if not input_path.exists():
                printc(
                    f"[{self.name}] Error: Input file {input_path} not found.",
                    level="error",
                    use_tqdm=True,
                )
                logging.warning(f"[{self.name}] Input file {input_path} not found.")
                return
            with open(input_path, "r") as f:
                urls = [line.strip() for line in f if line.strip()]

        elif url_provided:
            if wayback.lower() == "true":
                urls = shared_data.get("wayback_urls", [])
                if not urls:
                    printc(
                        f"[{self.name}] Warning: No URLs found from previous module.",
                        level="warn",
                        use_tqdm=True,
                    )
                    return
            elif wayback.lower() == "false":
                urls = [self.options.get("url", "").strip()]
            else:
                printc(
                    f"[{self.name}] Warning: Required option for wayback is True/False,"
                    " please use one of them.",
                    level="warn",
                    use_tqdm=True,
                )
                return

        output_path = Path(self.options["output_directory"])
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        hash_val = hash_url(self.options["url"])
        subdir_name = Path(input_file_path).stem if input_file_path else hash_val
        full_output_path = output_path / subdir_name / timestamp
        headless = self.options["headless"].lower() == "true"
        retry_count = int(self.options["retry_count"])
        thread_count = int(self.options["thread_count"])
        page_load_timeout = int(self.options["page_load_timeout"])

        full_output_path.mkdir(parents=True, exist_ok=True)
        error_log = output_path / subdir_name / f"error_urls-{timestamp}.txt"

        # printc(f"DEBUG: {len(urls)}", level="debug")
        progress = tqdm(total=len(urls), desc="Taking screenshots")
        success_counter = [0]
        progress_lock = threading.Lock()

        def take_screenshot(i, url):
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu-compositing")
            options.add_argument("--disable-extensions")
            # options.add_argument('--remote-debugging-port=0')
            options.add_argument("--log-level=3")  # Only fatal errors
            options.add_argument("--disable-logging")
            options.add_argument("--disable-extensions")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            if headless:
                options.add_argument("--headless=new")

            browser = None
            for attempt in range(retry_count):
                try:
                    browser = webdriver.Chrome(options=options)
                    browser.set_page_load_timeout(page_load_timeout)
                    browser.get(url)
                    screenshot_file = full_output_path / f"screenshot_{i}.png"
                    browser.save_screenshot(str(screenshot_file))
                    browser.quit()

                    with progress_lock:
                        msg = Text("[+] Captured screenshot for ") + colorize(
                            url, "cyan", "underline"
                        )
                        printc(msg, level="success", use_tqdm=True)
                        logging.info(f"[{self.name}] Screenshot captured: {url}")
                        success_counter[0] += 1
                        progress.update(1)
                    return
                except Exception as e:
                    with progress_lock:
                        msg = (
                            colorize("[!]", "bright_red", "bold")
                            + Text(f" Attempt {attempt + 1} failed for ")
                            + colorize(url, "red", "underline")
                        )
                        # printc(msg, use_tqdm=True)
                        logging.warning(
                            f"[{self.name}] Attempt {attempt + 1} failed for "
                            f"{url} - {str(e)}"
                        )
                        # progress.update(1)
                    if browser:
                        browser.quit()
            with open(error_log, "a") as ef:
                ef.write(url + "\n")

        threads = []
        for i, url in enumerate(urls):
            t = threading.Thread(target=take_screenshot, args=(i, url))
            threads.append(t)
            t.start()
            if len(threads) >= thread_count:
                for t in threads:
                    t.join()
                threads = []

        for t in threads:
            t.join()

        total = len(urls)
        success = success_counter[0]
        fail = total - success

        printc(
            Text(f"[{self.name}] Screenshots saved to ")
            + colorize(str(full_output_path), "green", "underline"),
            use_tqdm=True,
        )
        printc(
            Text(f"[{self.name}] Errors logged to ")
            + colorize(str(error_log), "red", "underline"),
            use_tqdm=True,
        )
        printc(
            f"[{self.name}] Screenshot job completed.", level="success", use_tqdm=True
        )
        printc(f"[✓] Total: {total}", level="info", use_tqdm=True)
        printc(f"[✓] Success: {success}", level="success", use_tqdm=True)
        printc(
            f"[✗] Failed: {fail} (saved to error_links.txt)",
            level="warn",
            use_tqdm=True,
        )

        logging.info(f"[{self.name}] Screenshots saved to {output_path}")
        logging.info(f"[{self.name}] Errors logged to {error_log}")
        logging.info(
            f"[{self.name}] Summary - Total: {total}, "
            f"Success: {success}, Failed: {fail}"
        )

        shared_data["last_summary"] = {
            "module": self.name,
            "total": total,
            "success": success,
            "fail": fail,
            "output_dir": str(full_output_path),
        }

    def print_summary(self, summary):
        try:
            print(f"Total     : {summary.get('total', 0)}")
            print(f"Success   : {summary.get('success', 0)}")
            print(f"Failed    : {summary.get('fail', 0)}")
            print(f"Directory : {summary.get('output_dir', '-')}")
        except Exception as e:
            logging.error(f"Error: {str(e)}")
