import argparse
import re
import requests
import concurrent.futures

def extract_words_from_text(text):
    words = re.findall(r'\b\w+\b', text)  # Adjusted regex to match whole words
    return words

def extract_words_hyphen_from_text(text):
    hyphen_words = re.findall(r'\b\w+(?:-\w+)+\b', text)
    return hyphen_words

def extract_filenames_from_text(text):
    filenames = re.findall(r'\b\w+\.(?:3g2|3gp|7z|ai|aif|apk|arj|asp|aspx|avi|bak|bat|bin|bmp|cab|cda|cer|cfg|cfm|cgi|class|cpl|cpp|css|csv|cur|dat|db|dbf|deb|dll|dmg|dmp|doc|docx|drv|email|eml|emlx|exe|flv|fnt|fon|gadget|gif|git|h264|hta|htm|html|icns|ico|inc|ini|iso|jar|java|jhtml|jpeg|jpg|js|jsa|jsp|key|lnk|log|m4v|mdb|mid|mkv|mov|mp3|mp4|mpa|mpeg|mpg|msg|msi|nsf|odp|ods|odt|oft|ogg|ost|otf|part|pcap|pdb|pdf|phar|php|php2|php3|php4|php5|php6|php7|phps|pht|phtml|pkg|pl|png|pps|ppt|pptx|ps|psd|pst|py|rar|reg|rm|rpm|rss|rtf|sav|sh|shtml|sql|svg|swf|swift|sys|tar|targz|tex|tif|tiff|tmp|toast|ttf|txt|vb|vcd|vcf|vob|wav|wma|wmv|wpd|wpl|wsf|xhtml|xls|xlsm|xlsx|xml|z|zip|json)\b', text)
    return filenames

def extract_words_from_url(url, headers=None):
    response = requests.get(url, headers=headers, allow_redirects=False)  # Passing headers to requests.get()
    if response.status_code == 200:
        text = response.text
        words = extract_words_from_text(text)
        hyphen_words = extract_words_hyphen_from_text(text)
        filenames = extract_filenames_from_text(text)
        return words, hyphen_words, filenames
    else:
        print(f"Failed to retrieve data from URL: {url}")
        return [], [], []

def process_urls_from_file(file_path, num_threads, headers=None):
    with open(file_path, 'r') as file:
        urls = file.readlines()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(extract_words_from_url, url.strip(), headers) for url in urls]
            for future in concurrent.futures.as_completed(futures):
                words, hyphen_words, filenames = future.result()
                print_words(words)
                print_hyphenated_words(hyphen_words)
                print_filenames(filenames)

def print_words(words):
    for word in words:
        print(word)
        if "_" in word:
            pieces = word.split("_")
            for piece in pieces:
                print(piece)

def print_hyphenated_words(hyphen_words):
    for word in hyphen_words:
        print(word)

def print_filenames(filenames):
    for filename in filenames:
        print(filename)

def main():
    parser = argparse.ArgumentParser(description="Extract and display words and filenames from a text file or URL.")
    parser.add_argument("-f", "--file", help="Path to the text file.")
    parser.add_argument("-u", "--url", help="URL to retrieve text from.")
    parser.add_argument("-l", "--url_list", help="Path to a file containing a list of URLs.")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Number of threads to use for sending HTTP requests.")
    parser.add_argument("-H", "--headers", help="Custom HTTP headers as a string in the format 'key1:value1,key2:value2'")
    args = parser.parse_args()

    headers = {}
    if args.headers:
        header_list = args.headers.split(",")
        for header in header_list:
            parts = header.split(":", 1)
            if len(parts) == 2:
                key, value = parts
                headers[key.strip()] = value.strip()
            else:
                print(f"Ignoring invalid header: {header}")

    if args.file:
        with open(args.file, 'r') as file:
            text = file.read()
            words = extract_words_from_text(text)
            hyphen_words = extract_words_hyphen_from_text(text)
            filenames = extract_filenames_from_text(text)
            print_words(words)
            print_hyphenated_words(hyphen_words)
            print_filenames(filenames)
    elif args.url:
        words, hyphen_words, filenames = extract_words_from_url(args.url, headers=headers)
        print_words(words)
        print_hyphenated_words(hyphen_words)
        print_filenames(filenames)
    elif args.url_list:
        process_urls_from_file(args.url_list, args.threads, headers=headers)
    else:
        print("Please provide either a file path, a URL, or a file containing a list of URLs.")

if __name__ == "__main__":
    main()
