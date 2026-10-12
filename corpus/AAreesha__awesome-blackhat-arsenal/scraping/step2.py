import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Load previous metadata
with open("metadata_only.json", "r", encoding="utf-8") as f:
    tools = json.load(f)

options = Options()
# options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

driver.get("https://www.blackhat.com/us-23/arsenal/schedule/index.html")
time.sleep(5)

for tool in tools:
    tool_id = tool.get("tool_id")
    if not tool_id:
        continue

    try:
        link_elem = driver.find_element(By.CSS_SELECTOR, f'a[data-id="{tool_id}"]')
        driver.execute_script("arguments[0].click();", link_elem)

        desc_div_id = f"session_desc_{tool_id}"
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, desc_div_id))
        )
        desc_el = driver.find_element(By.CSS_SELECTOR, f"#{desc_div_id} .description")
        tool["description"] = desc_el.get_attribute("innerText").strip()

    except TimeoutException:
        print(f"❌ Timeout for tool_id: {tool_id}")
        tool["description"] = None
    except Exception as e:
        print(f"⚠️ Error for tool_id: {tool_id} – {e}")
        tool["description"] = None

driver.quit()

with open("arsenal_tools_2023.json", "w", encoding="utf-8") as f:
    json.dump(tools, f, indent=2, ensure_ascii=False)

print("✅ Step 2 complete: Descriptions added.")
