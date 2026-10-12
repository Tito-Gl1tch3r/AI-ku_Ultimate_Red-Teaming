import os
import sqlite3
import shutil
import glob
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

# 8/13/2025
# Get all History Searches on [ Microsoft , Chrome , Firefox ]
# AUX-441


class get_history_search:
    @staticmethod
    def chrome_time_to_datetime(chrome_time):
        if chrome_time:
            return datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)
        return None

    @staticmethod
    def extract_search_query(url):
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            if 'q' in qs:
                return qs['q'][0]
            elif 'p' in qs:
                return qs['p'][0]
        except:
            pass
        return None

    @staticmethod
    def get_chrome_searches(history_path, browser_name):
        searches = []
        if not os.path.exists(history_path):
            return searches
        temp_path = history_path + "_temp"
        shutil.copy2(history_path, temp_path)
        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT url, title, last_visit_time
                FROM urls
                WHERE url LIKE '%/search?q=%'
                OR url LIKE '%bing.com/search?q=%'
                OR url LIKE '%yahoo.com/search?p=%'
            """)
            for url, title, visit_time in cursor.fetchall():
                query = get_history_search.extract_search_query(url)
                date_time = get_history_search.chrome_time_to_datetime(visit_time)
                searches.append({
                    "browser": browser_name,
                    "query": query,
                    "url": url,
                    "time": date_time.strftime("%Y-%m-%d %H:%M:%S") if date_time else "Unknown"
                })
        except Exception as e:
            print(f"[{browser_name}] Error:", e)
        conn.close()
        os.remove(temp_path)
        return searches

    @staticmethod
    def get_firefox_searches(profile_dir):
        searches = []
        for profile in glob.glob(os.path.join(profile_dir, "*")):
            history_path = os.path.join(profile, "places.sqlite")
            if not os.path.exists(history_path):
                continue
            temp_path = history_path + "_temp"
            shutil.copy2(history_path, temp_path)
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT url, last_visit_date
                    FROM moz_places
                    WHERE url LIKE '%/search?q=%'
                    OR url LIKE '%bing.com/search?q=%'
                    OR url LIKE '%yahoo.com/search?p=%'
                """)
                for url, visit_time in cursor.fetchall():
                    query = get_history_search.extract_search_query(url)
                    if visit_time:
                        date_time = datetime(1970, 1, 1) + timedelta(microseconds=visit_time)
                    else:
                        date_time = None
                    searches.append({
                        "browser": "Firefox",
                        "query": query,
                        "url": url,
                        "time": date_time.strftime("%Y-%m-%d %H:%M:%S") if date_time else "Unknown"
                    })
            except Exception as e:
                print("[Firefox] Error:", e)
            conn.close()
            os.remove(temp_path)
        return searches

    @staticmethod
    def run_search_history(output_path="full_informations", output_file="search.txt"):
        started_time = datetime.now()
        print("Started Time for Searches:", started_time)

        user_dir = os.getenv("USERPROFILE")
        chrome_history = os.path.join(user_dir, r"AppData\Local\Google\Chrome\User Data\Default\History")
        edge_history = os.path.join(user_dir, r"AppData\Local\Microsoft\Edge\User Data\Default\History")
        firefox_profiles = os.path.join(user_dir, r"AppData\Roaming\Mozilla\Firefox\Profiles")

        all_searches = []
        all_searches.extend(get_history_search.get_chrome_searches(chrome_history, "Chrome"))
        all_searches.extend(get_history_search.get_chrome_searches(edge_history, "Edge"))
        all_searches.extend(get_history_search.get_firefox_searches(firefox_profiles))

        os.makedirs(output_path, exist_ok=True)
        full_path = os.path.join(output_path, output_file)

        with open(full_path, "w", encoding="utf-8") as f:
            for item in all_searches:
                f.write(f"[{item['time']}] ({item['browser']}) Search: {item['query']}\nURL: {item['url']}\n\n")

        print(f"{len(all_searches)} search entries saved to {full_path}")



if __name__ == "__main__":
    get_history_search.run_search_history()
