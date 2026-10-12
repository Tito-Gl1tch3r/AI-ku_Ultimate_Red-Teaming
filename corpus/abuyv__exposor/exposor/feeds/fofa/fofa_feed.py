import requests
import logging
import base64
import sys
from urllib.parse import quote
from datetime import datetime


class Fofa:
    def auth(email, api_key):
        try:
            headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Accept": "application/json"
            }

            credits = 0
            response = requests.get(f"https://fofa.info/api/v1/info/my?email={email}&key={api_key}", headers=headers)
            if response.status_code == 200 and 'username' in response.json():
                js = response.json()
                logging.debug(f"Fofa response body: {response.content.decode('utf-8')}")
                logging.info("Authentication successful for fofa")
                #credits = js["quota"]["allowance"] - js["quota"]["used"]
                #logging.info(f"Available credits are: {credits}")
                credits = response.json()['remain_api_query']
                logging.info(f"Fofa - remaining credits: {credits}")

                return True
            else:
                return False
        except Exception as e:
            logging.error(str(e))
            return False

    def search(email, key, queries, args, technology):
        session = requests.session()
        results = []
        page = 0
        limit_result = args.limit
        query_limit = args.query_limit
        country_code = args.country
        net = args.netblock
        domain_name = args.domain_name

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip"
            }

        try:
            for q in queries:
                if net:
                    q = f"{q} && ip={net}"

                if country_code:
                    q = f"{q} && country=\"{country_code}\""

                if domain_name:
                    q = f"{q} && host=\"{domain_name}\""

                page = 1
                counter = 0

                while counter < int(limit_result):
                    keyword = quote(str(base64.b64encode(q.encode()), encoding='utf-8'))
                    url = "https://fofa.info/api/v1/search/all?email={0}&key={1}&qbase64={2}&page={3}&full=false&fields=ip,domain,port,country,banner,title,header".format(
            email, key, keyword, page)
                    response = requests.get(url, timeout=10, headers=headers)
                    
                    if response.status_code != 200 or response.json()['error']:
                        logging.debug(f"Fofa - we got the error when sending request of {q}")
                        break
                    
                    banners = response.json()
                    matches = banners.get('results', [])
                    total_tech = len(matches)
                    logging.debug(f"Fofa - total result: {total_tech} for query: {q}")

                    if total_tech == 0:
                        break

                    remaining = int(limit_result) - counter
                    matches_to_add = matches[:remaining]

                    for banner in matches_to_add:
                        counter += 1
                        if counter > int(limit_result):
                            break
                        # todo: timestamp needs to be patched
                        banner_dic = {
                            'ip':banner[0],
                            'domain': banner[1],
                            'port': banner[2],
                            'country': banner[3],
                            'technology': technology,
                            'feed': 'fofa',
                            'timestamp': datetime.now()
                        }
                        results.append(banner_dic)
                    page += 1

                if query_limit.lower() == "yes":
                    break
            return results
        except Exception as e:
            logging.error(f"ERROR fofa search {e}")

        return results
