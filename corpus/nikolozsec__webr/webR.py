import os, sys, stat
import socket
import platform
import requests
import tldextract
import pandas as pd
from datetime import datetime
from pandas import ExcelFile
from pandas import ExcelWriter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Check OS and use relevant driver
if platform.system() == 'Windows':
    chrome_driver = '.\\driver\\chromedriver.exe'
elif platform.system() == 'Darwin':
    chrome_driver = './driver/chromedriver_mac64'
else:
    chrome_driver = './driver/chromedriver_linux64'

# Define time format for unique screenshot file names
screenshot_time = datetime.strftime(datetime.now(), ' %Y-%m-%d %H-%M-%S')

# Chrome Driver configuration for taking screenshots
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-infobars")  
chrome_options.add_argument("--disable-extensions") 
chrome_options.add_argument("--window-size=1366,768")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument('--ignore-certificate-errors')

# Ask for screenshots
take_screens = input("Take website screenshots? (Chrome required) [1] For all websites [2] Only for non HTTP 200 responses (for errors) [3] No screenshots: ")

# Ask for file
input_file = './domains.xlsx'
input_column = 'input_urls'
output_file = './results.xlsx'

# File location
src = pd.read_excel(input_file)
column = src[input_column]

# Count number of rows in excel file
countRow = src.shape[0]

# Create empty list
url_list = []
code_list = []
ip_list = []

# Print a message

print("\n" + "=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=  \n" + "=     webr by Nikoloz Kokhreidze | @nikolozsec    = \n" + "=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=  \n")
print("CHECKING {} ITEMS: \n".format(countRow))


# Go throught the File
for i in src.index:

# Separates the gTLD or ccTLD from the registered domain and subdomains of a URL
    domain_extract = tldextract.extract(column[i])
    domain = domain_extract.domain + '.' + domain_extract.suffix
    httpUrl = 'http://' + domain

# Add URLs to the list
    url_list.append(httpUrl)

# Get IP from domain
    try:
        ip = socket.gethostbyname(domain)
        ip_list.append(ip)

# If socket.error, write error in excel
    except socket.error as error:
        ip_list.append("socket error")
        ip = "socket error"

# Try to send request
    try:
        r = requests.get(httpUrl, stream=True)
        status = r.status_code
        code_list.append(status)

# If ConnectionError, write error in excel
    except requests.ConnectionError as error: 
        code_list.append("connection error")
        status = "connection error"

# Take screenshots based on user input
    if take_screens == '1':
        driver = webdriver.Chrome(options=chrome_options, executable_path=chrome_driver)
        driver.get(column[i])
        driver.save_screenshot(os.path.join('screenshots', domain + screenshot_time + '.png'))
        driver.close()

    elif take_screens == '2' and status != 200:        
        driver = webdriver.Chrome(options=chrome_options, executable_path=chrome_driver)
        driver.get(column[i])
        driver.save_screenshot(os.path.join('screenshots', domain + screenshot_time + '.png'))
        driver.close()

    print(str(domain) + " -  " + str(status) + " - " + str(ip))
    
# Put output in data
data = {'URL': url_list, 'STATUS': code_list, 'IP': ip_list}

# Create a dataframe and write to new excel file
df = pd.DataFrame(data=data, index=None)
print("\n" + "=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=  \n" + "=                   RESULTS                       = \n" + "=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=  \n" + str(df))
writer = ExcelWriter(output_file)
df.to_excel(writer,'webr', index=False)
writer.save()
