# modules/pb_holehe_check_email.py
from modules.base import BaseModule
from core.utils.formatter import printc
from core.utils.progress_bar import create_spinner, progress_bar
from core.contrib.holehe_async_runner import run_holehe_modules

import trio
import time


class Module(BaseModule):
    def __init__(self):
        super().__init__()

        self.name = "pb_holehe_check_email"
        self.description = (
            "Checks email addresses across various online platforms using holehe."
        )
        self.category = "osint"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = "https://github.com/bkili"
        self.license = "<License>"
        self.version = "<Version>"

        self.default_options = {
            "e-mail": "test@example.com",
            "verbose": "False",
            "debug": 0,
        }

        self.required_options = ["e-mail"]

        self.options = self.default_options.copy()

    def requires(self):
        return []

    def run(self, shared_data):
        try:
            verbosity_level = self.options.get("verbose").strip().lower()
            email = self.options.get("e-mail").strip()
            debug_str = self.options.get("debug")

            try:
                debug_mode = int(debug_str)
            except (TypeError, ValueError):
                printc("[!] Please provide debug mode as 0, 1 or 2", level="warn")
                return

            if debug_mode not in (0, 1, 2):
                printc("[!] Debug level must be 0, 1 or 2", level="warn")
                return

            if not isinstance(email, str) or not email.strip():
                printc("[!] Please provide proper email.", level="warn")
                return

            if not verbosity_level.isalpha() or verbosity_level.lower() not in (
                "true",
                "false",
            ):
                printc("[!] Please provide verbose level [True/False]", level="warn")
                return

            # Banner
            printc(f"\n{len(email) * '#'}", level="module")
            printc(f"{email}", level="selection")
            printc(f"{len(email) * '#'}\n", level="module")

            spinner = "braille"
            spinner_cycle = create_spinner(spinner)
            start_time = time.time()
            bar_len = 40
            out = []

            # Run holehe modules in parallel using generic runner
            results = trio.run(
                run_holehe_modules,
                email,
                "holehe.modules",
                out,
                debug_mode,
                lambda c, t: progress_bar(bar_len, c, t, start_time, spinner_cycle),
            )

            valid_hits = []
            invalid_hits = []

            for r in results:
                is_exists = r.get("exists")
                if is_exists:
                    valid_hits.append(r)
                else:
                    invalid_hits.append(r)

            # print results
            print()
            for not_hit in invalid_hits:
                name = not_hit.get("name")
                printc(f"[-] {name}", level="unsuccessful")

            if valid_hits:
                for hit in valid_hits:
                    # Meta Data
                    name = hit.get("name")
                    domain = hit.get("domain")
                    method = hit.get("method")
                    frequent_rate_limit = hit.get("frequent_rate_limit")
                    rate_limit = hit.get("rateLimit")
                    email_recovery = hit.get("emailrecovery")
                    phone_number = hit.get("phoneNumber")
                    others = hit.get("others")

                    printc(f"[+] {name}", level="success")
                    if verbosity_level == "true":
                        printc(f"    └── Domain: {domain}", level="info")
                        printc(f"    └── Method: {method}", level="info")
                        printc(
                            f"    └── Frequent Rate Limit: {frequent_rate_limit}",
                            level="info",
                        )
                        printc(f"    └── Rate Limit: {rate_limit}", level="info")
                        printc(
                            f"    └── Email Recovery: {email_recovery}", level="info"
                        )
                        printc(f"    └── Phone Number: {phone_number}", level="info")
                        printc(f"    └── Others: {others}", level="info")

        except Exception as e:
            printc(f"[{self.name}] Error during execution: {e}", level="error")

    def print_summary(self, summary):
        try:
            printc(f"Summary for {self.name}:", level="headline")
            printc(str(summary), level="info")
        except Exception as e:
            printc(f"[{self.name}] Failed to print summary: {e}", level="error")
