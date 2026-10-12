import csv
import codecs
from datetime import datetime
import requests
import json
import time
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from pycti import OpenCTIApiClient
from .utils import *
from .config import load_config
import win32api
import win32con


class Harpoon:
    config = load_config()
    URLSCAN_SCAN_URL = config['urlscan']['scan_url']
    URLSCAN_RESULT_URL = config['urlscan']['result_url']
    URLSCAN_RESULT_URL_UI = config['urlscan']['result_url_ui']
    URLSCAN_SEARCH_URL = config['urlscan']['search_url']
    URLSCAN_API_KEY = config['urlscan']['api_key']
    OPENCTI_DOMAIN = config['opencti']['domain']
    OPENCTI_API_KEY = config['opencti']['api_key']
    AUTOMATED_PHISHING_TRACKER_ID = config['opencti']['automated_phishing_tracker_id']
    INTEL_PURPLE = config['opencti']['intel_purple']
    TOP_1M_PATH = config['top_1M']['path']
    HEADERS = {'API-Key': URLSCAN_API_KEY, 'Content-Type': 'application/json'}

    def __init__(self, url):
        print(self.OPENCTI_DOMAIN)
        self.starting_url = url
        self.current_url = url
        self.continue_analysis = True
        self.signatures = {}
        self.hashes = {}
        self.driver = None
        self.first_time = True
        self.human_interaction = -1
        self.opencti_client = OpenCTIApiClient(
            url=self.OPENCTI_DOMAIN, token=self.OPENCTI_API_KEY)
        self.urls_to_submit = set()
        try:
            with open(self.TOP_1M_PATH, 'rb') as file:
                reader = csv.reader(codecs.iterdecode(file, "utf-8"))
                self.legit_domains = set()
                for rank, domain in reader:
                    self.legit_domains.add(domain.strip())
        except Exception as e:
            print(f"{e}")

    @staticmethod
    def click(x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    # def click_link(self, href):
    #     original_window = self.driver.current_window_handle
    #     # TODO take more than one link and if cloudflare hits, resubmit
    #     href.click()
    #     WebDriverWait(self.driver, 10).until(
    #         EC.new_window_is_opened([original_window]))

    #     new_windows = self.driver.window_handles
    #     for window in new_windows:
    #         if window != original_window:
    #             self.driver.switch_to.window(window)
    #             break

    @staticmethod
    def url_to_domain(url):
        return urlparse(url).hostname

    @staticmethod
    def url_to_filename(url):
        parsed_url = urlparse(url)
        path = parsed_url.path
        filename = os.path.basename(path)
        if not filename:
            filename = "primary_request"
        return filename

    @staticmethod
    def defang_url(url):
        return url.replace(".", "[.]")

    def is_cloudflare(self):
        scripts = self.driver.find_elements(By.XPATH, '//head//script[@src]')
        return any('challenges.cloudflare' in s.get_attribute('src') for s in scripts)

    def is_custom_captcha(self):
        try:
            checkbox = self.driver.find_element(
                By.XPATH, '//input[@type="checkbox"]')
            if checkbox:
                return True
        except Exception:
            pass
        return False

    def is_notion(self):
        domain = self.url_to_domain(self.current_url)
        if "notion.site" in domain:
            return True
        return False

    # def is_generic_link(driver):
    #     link_elements = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    #     all_links = [(a.get_attribute("href"), a.text.strip())
    #                  for a in link_elements]
    #     for href, label in all_links:
    #         # TODO: check if the link is malicious better
    #         if ".ru" in href:
    #             return True
    #     return False

    # def is_generic_button(self):
    #     # button_elements = driver.find_elements(By.CSS_SELECTOR, 'button[type="button"]')
    #     button_elements = self.driver.find_elements(By.TAG_NAME, "button")
    #     buttons = [btn.text.strip() for btn in button_elements]
    #     for i, text in enumerate(buttons):
    #         # if text in ["Scarica", "Download", "Download file"]:
    #         return True
    #     return False

    def is_custom_human_interaction(self):
        has_checkbox = len(self.driver.find_elements(
            By.XPATH, "//input[@type='checkbox']")) > 0
        has_text_input = len(self.driver.find_elements(
            By.XPATH, "//input[@type='text']")) > 0
        has_button = len(self.driver.find_elements(By.TAG_NAME, "button")) > 0
        if has_checkbox or has_text_input or has_button:
            return True
        return False

    def is_asking_password(self):
        return len(self.driver.find_elements(By.XPATH, "//input[@type='password']")) > 0

    def check_if_human_interaction(self):
        try:
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script(
                    "return document.readyState") == "complete"
            )
        except Exception:
            human_interaction = -1
        time.sleep(5)
        if self.is_cloudflare():
            human_interaction = 1
        elif self.is_asking_password():
            human_interaction = 0
        elif self.is_custom_human_interaction():
            human_interaction = 6
        # elif is_custom_captcha(self.driver):
        #     human_interaction = 2
        elif self.is_notion():
            human_interaction = 3
        # elif is_generic_link(self.driver):
        #     human_interaction = 4
        # elif is_generic_button(self.driver):
        #     human_interaction = 5
        else:
            human_interaction = 0
        self.human_interaction = human_interaction
        print("Human interaction detected:", self.human_interaction)
        return self.human_interaction

    def bypass_human_interaction(self):
        time.sleep(5)
        match self.human_interaction:
            case 0:
                pass
            case 1:
                self.click(862, 296)
                time.sleep(0.5)
                self.click(838, 296)
                time.sleep(0.5)
                self.click(862, 185)
                time.sleep(0.5)
                self.click(865, 226)
                time.sleep(0.5)
                self.click(866, 257)
                time.sleep(0.5)
                self.click(863, 149)
                time.sleep(0.5)
            case 2:
                try:
                    checkbox = self.driver.find_element(
                        By.XPATH, '//input[@type="checkbox"]')
                    actions = ActionChains(self.driver)
                    actions.move_to_element(checkbox).click().perform()
                except Exception as e:
                    pass
            case 3:
                proceed_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "proceed anyway")))
                proceed_link.click()
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a.notion-link-token"))
                )
                time.sleep(1)
                link_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "a.notion-link-token")
                # click_link(driver, link_elements[0])
            case 4:
                link_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "a[href]")
                all_links = [(a.get_attribute("href"), a.text.strip())
                             for a in link_elements]
                for href, label in all_links:
                    # TODO: check if the link is malicious better
                    if ".ru" in href:
                        # click_link(driver, href)
                        return True
            case 5:
                # button_elements = driver.find_elements(By.CSS_SELECTOR, 'button[type="button"]')
                button_elements = self.driver.find_elements(
                    By.TAG_NAME, "button")
                buttons = [btn.text.strip() for btn in button_elements]
                for i, text in enumerate(buttons):
                    # if text in ["Scarica", "Download", "Download file", "Access"]:
                    button_elements[i].click()
            case 6:
                # checkboxes
                checkboxes = self.driver.find_elements(
                    By.XPATH, "//input[@type='checkbox']")
                for checkbox in checkboxes:
                    if not checkbox.is_selected():
                        try:
                            checkbox.click()
                        except Exception:
                            pass
                # text inputs
                text_inputs = self.driver.find_elements(
                    By.XPATH, "//input[@type='text' or @type='email']")
                for text_input in text_inputs:
                    # if text_input.is_enabled():
                    try:
                        text_input.clear()
                        text_input.send_keys("test@outlook.com")
                    except Exception:
                        pass
                # buttons
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if not "back" in button.get_attribute("class").lower():
                        try:
                            button.click()
                        except Exception:
                            pass
            case -1:
                print("Page load timed out.")
                return None
            case _:
                print("???")
                return None
        time.sleep(10)
        return

    def open_browser(self):
        options = uc.ChromeOptions()
        # options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")  # consigliato su Windows
        options.add_argument("--start-maximized")
        # options.add_argument('window-size=1920x1080')
        self.driver = SafeChrome(options=options)
        # Set window size and position
        self.driver.set_window_position(0, 0)
        # driver.set_window_size(1920, 1080)
        self.driver.get(self.starting_url)
        return

    def close_browser(self):
        self.driver.quit()

    def collect_url(self, after_bypass):
        if after_bypass:
            landed_url = self.driver.current_url
            if landed_url == self.current_url and self.human_interaction > 0:
                print("Waiting for URL to change...")
                attempts = 1
                while landed_url == self.current_url:
                    time.sleep(1)
                    landed_url = self.driver.current_url
                    attempts += 1
                    if attempts > 10:
                        # Stop the script
                        self.continue_analysis = False
                        return
            self.current_url = landed_url
        if not self.is_legit_url(self.current_url):
            self.urls_to_submit.add(self.current_url)

    def urlscan_submit(self, url):
        data = {"url": url, "visibility": "public"}
        response = requests.post(
            self.URLSCAN_SCAN_URL, headers=self.HEADERS, data=json.dumps(data))
        uuid = response.json().get("uuid", 0)
        return uuid

    def urlscan_fetch_results(self, uuid):
        url = self.URLSCAN_RESULT_URL + f"{uuid}"
        time.sleep(10)
        response = requests.get(url, headers=self.HEADERS)
        while response.status_code == 404:
            time.sleep(2)
            response = requests.get(url, headers=self.HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch result: {response.status_code}")
            return
        data = response.json()
        hashes = data["lists"]["hashes"]
        urls = data["lists"]["urls"]
        results = {}
        for hash_value, url in zip(hashes, urls):
            file_name = self.url_to_filename(url)
            results[file_name] = hash_value
        return results

    def is_legit_url(self, url):
        domain = self.url_to_domain(url)
        return domain in self.legit_domains

    def submit_urls(self):
        for url in self.urls_to_submit:
            print("Submitting URL:", self.defang_url(url))
            uuid = self.urlscan_submit(url)
            if uuid != 0:
                print(f"\tResults: {self.URLSCAN_RESULT_URL_UI}{uuid}/")
                self.hashes.update(self.urlscan_fetch_results(uuid))
            else:
                print(f"\tError in submitting url")

    def check_valid_signature(self):
        for file_name, hash in self.hashes.items():
            url = self.URLSCAN_SEARCH_URL + f"?q=hash:{hash}"

            response = requests.get(url, headers=self.HEADERS)
            data = response.json()
            results = data["total"]

            if results > 1 and results < 1000:
                self.signatures[file_name] = hash
                print(
                    f"\tThe file {file_name} (hash:{hash}) has been seen in {results} samples.")

    def opencti_load_signatures(self):
        if len(self.signatures) == 0:
            print("\tNo valid signatures found.")
        else:
            for file_name, hash in self.signatures.items():
                # Create note in OpenCTI with the signature
                content = json.dumps(
                    {"tags": ["hunt-u", "generic_phishing_kit"],
                     "signature": f"hash:{hash} AND NOT page.domain:\"login.microsoftonline.com\" AND NOT page.domain:\"microsoft.com\" AND NOT page.domain:\"live.com\" AND NOT page.domain:\"office.com\" AND NOT page.domain:\"outlook.com\" AND NOT page.domain:\"sharepoint.com\" AND NOT page.domain:\"windows.net\"",
                     "note": "Firma creata dall'automation Silent Harpoon"}
                )
                self.opencti_client.note.create(abstract=f"Generic Phishing kit {datetime.now().strftime('%Y%m%d_%H%M%S')} | Tool | {file_name}", content=content, note_types=[
                                                "HUNTING URLSCAN"], objects=[self.AUTOMATED_PHISHING_TRACKER_ID], objectMarking=[self.INTEL_PURPLE])
            print("Signatures loaded to OpenCTI")

    # TODO: custom urlscan???
    def run(self):
        print("Silent Harpoon started for:",
              self.defang_url(self.starting_url))
        self.open_browser()
        while (self.check_if_human_interaction() > 0 or self.first_time) and self.continue_analysis:
            self.current_url = self.driver.current_url
            # Add page to urls to scan if human interaction is detected, must be the first time
            if self.human_interaction > 0 and self.first_time:
                self.collect_url(after_bypass=False)
            self.first_time = False
            # Bypass human interaction
            self.bypass_human_interaction()
            # Add landed page to urls to scan
            self.collect_url(after_bypass=True)
        # Submit collected urls
        self.submit_urls()
        # Create signatures
        self.check_valid_signature()
        # Submit signatures to OpenCTI
        self.opencti_load_signatures()
        # Close Browser
        self.close_browser()
