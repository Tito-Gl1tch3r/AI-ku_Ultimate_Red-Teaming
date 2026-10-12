import requests, json, os


class VirusTotal:
    def __init__(self, api_key):
        self.api_key = os.getenv("VTAPIKEY")
        self.base_url = "https://www.virustotal.com/api/v3/"

    def Make_Request(self, endpoint):
        headers = {"x-apikey": self.api_key, "accept": "application/json"}
        try:
            response = requests.get(self.base_url + endpoint, headers=headers)
            if response.status_code == 200:
                jsonresponse = json.loads(response.text)
                return jsonresponse
            else:
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def get_ip_report(self, ip_address):
        endpoint = f"ip_addresses/" + ip_address
        ip_report = self.Make_Request(endpoint)
        lastanalysisdate = ip_report["data"]["attributes"]["last_analysis_date"]
        filereputation = ip_report["data"]["attributes"]["reputation"]
        whois = ip_report["data"]["attributes"]["whois"]
        last_analysis_results = ip_report["data"]["attributes"]["last_analysis_results"]
        analysis_list = []
        malicious_count = 0
        for index, key in last_analysis_results.items():
            if isinstance(key, dict):
                for analysis, result in key.items():
                    if analysis == "category":
                        analysis_list.append(result)
        numberofreports = len(analysis_list)
        for verdict in analysis_list:
            if verdict == "malicious":
                malicious_count += 1
        if numberofreports > 0:
            malicious = True
            malicious_percentage = (malicious_count / numberofreports) * 100
        else:
            malicious_percentage = 0
        malicious_percentage_formatted = "{:.2f}%".format(malicious_percentage)
        data_dict = {
            "ipaddress": ip_address,
            "whois": whois,
            "lastanalysisdate": lastanalysisdate,
            "malicious": malicious,
            "malicious_percentage": malicious_percentage_formatted,
        }
        return data_dict

    def get_domain_report(self, domain):
        endpoint = f"domains/" + domain
        domain_report = self.Make_Request(endpoint)
        registrar = domain_report["data"]["attributes"]["registrar"]
        last_analysis_results = domain_report["data"]["attributes"][
            "last_analysis_results"
        ]
        analysis_list = []
        malicious_count = 0
        for index, key in last_analysis_results.items():
            if isinstance(key, dict):
                for analysis, result in key.items():
                    if analysis == "category":
                        analysis_list.append(result)
        numberofreports = len(analysis_list)
        for verdict in analysis_list:
            if verdict == "malicious":
                malicious_count += 1
        if numberofreports > 0:
            malicious = True
            malicious_percentage = (malicious_count / numberofreports) * 100
        else:
            malicious_percentage = 0
        malicious_percentage_formatted = "{:.2f}%".format(malicious_percentage)
        data_dict = {
            "registrar": registrar,
            "malicious_percentage": malicious_percentage_formatted,
        }
        return data_dict

    def get_url_report(self, url):
        endpoint = f"/urls/" + url
        url_report = self.Make_Request(endpoint)
        last_analysis_results = url_report["data"]["attributes"][
            "last_analysis_results"
        ]
        analysis_list = []
        malicious_count = 0
        for index, key in last_analysis_results.items():
            if isinstance(key, dict):
                for analysis, result in key.items():
                    if analysis == "category":
                        analysis_list.append(result)
        numberofreports = len(analysis_list)
        for verdict in analysis_list:
            if verdict == "malicious":
                malicious_count += 1
        if numberofreports > 0:
            malicious = True
            malicious_percentage = (malicious_count / numberofreports) * 100
        else:
            malicious_percentage = 0
        malicious_percentage_formatted = "{:.2f}%".format(malicious_percentage)
        data_dict = {
            "registrar": registrar,
            "malicious_percentage": malicious_percentage_formatted,
        }
        return data_dict

    def get_file_report(self, file_hash):
        endpoint = f"/files/" + file_hash
        file_report = self.Make_Request(endpoint)
        filename = file_report["data"]["attributes"]["names"]
        lastanalysisdate = file_report["data"]["attributes"]["last_analysis_date"]
        filereputation = file_report["data"]["attributes"]["reputation"]
        data_dict = {
            "filename": filename,
            "lastanalysisdate": lastanalysisdate,
            "filereputation": filereputation,
        }
        return data_dict
