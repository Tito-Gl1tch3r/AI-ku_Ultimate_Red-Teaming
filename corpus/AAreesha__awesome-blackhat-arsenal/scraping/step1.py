from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import json
import time

options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

driver.get("https://www.blackhat.com/us-23/arsenal/schedule/index.html")
time.sleep(5)

containers = driver.find_elements(By.CLASS_NAME, "data-container")
results = []

for tool in containers:
    def get_text_by_class(cls, prefix=""):
        try:
            return tool.find_element(By.CLASS_NAME, cls).text.replace(prefix, "").strip()
        except NoSuchElementException:
            return None

    try:
        link_elem = tool.find_element(By.CLASS_NAME, "sd_link")
        tool_name = link_elem.text.strip()
        tool_id = link_elem.get_attribute("data-id")
    except NoSuchElementException:
        tool_name = ""
        tool_id = None

    speakers = [s.text.strip() for s in tool.find_elements(By.CLASS_NAME, "speaker_link") if s.text.strip()]
    track_raw = get_text_by_class("session-track", "Tracks:")
    tracks = [t.strip() for t in track_raw.split(",")] if track_raw else None
    location = get_text_by_class("session-session-room", "Location:")
    skill_level = get_text_by_class("session-session-audience-level", "Skill Level:") or "All"
    session_type = get_text_by_class("session-session-type", "Session Type:")

    results.append({
        "tool_name": tool_name,
        "tool_id": tool_id,
        "speakers": speakers or None,
        "tracks": tracks,
        "location": location,
        "skill_level": skill_level,
        "event": "BH-USA-2023",
        "session_type": session_type,
        "github_url": None,
        "description": None
    })

driver.quit()

with open("metadata_only.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("✅ Step 1 complete: Metadata extracted and saved.")
