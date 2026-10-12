import requests
import logging
import json

# debugging
import sys


class Censys:
    def auth(CENSYS_API_ID, CENSYS_API_KEY):
        try:
            headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Accept": "application/json"
            }
            credits = 0

            response = requests.get("https://search.censys.io/api/v1/account", auth=(CENSYS_API_ID, CENSYS_API_KEY))
            if response.status_code == 200 and 'allowance' in response.text:
                js = response.json()
                logging.debug(f"Censys response body: {response.content.decode('utf-8')}")
                logging.info("Authentication successful for censys")
                credits = js["quota"]["allowance"] - js["quota"]["used"]
                logging.info(f"Censys - remaining credits for censys: {credits}")

                return True
            else:
                return False
        except Exception as e:
            logging.error(f"ERROR on censys authentication {e}")
            return False


    def search(uid, key, queries, args, technology):
        limit_result = args.limit
        query_limit = args.query_limit
        country_code = args.country
        net = args.netblock
        domain_name = args.domain_name
        results = []
        page = ""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Accept": "application/json"
            }

        try:

            for q in queries:
                if net:
                    q = f"{q} AND ip:{net}"

                if country_code:
                    q = f"{q} AND location.country_code=\"{country_code}\""

                if domain_name:
                    q = f"{q} AND dns.names:\"{domain_name}\""

                page = ""
                counter = 0
                while counter < int(limit_result):
                    url = f"https://search.censys.io/api/v2/hosts/search"
                    data = {
                    "q": q,
                    "sort": "RELEVANCE"
                    }
                    response = requests.post(url, headers=headers, data = json.dumps(data), auth=(uid,key))
                    if response.status_code != 200:
                        logging.debug(f"Request failed with status code: {response.status_code}")
                        break

                    banners = response.json()
                    if banners['result']['total'] == 0:
                        logging.info(f"Censys - we got 0 hits for query: {q}")
                        break

                    logging.debug(f"Censys - total result: {banners['result']['total']} for query: {q}")

                    matches = banners['result']['hits']

                    remaining = int(limit_result) - counter
                    matches_to_add = matches[:remaining]

                    for banner in matches_to_add:
                        services = banner.get('matched_services', [])
                        for service in services:
                            counter += 1

                            if 'tls' in service:
                                domain = service['tls']['certificates']['leaf_data']['subject_dn']
                            else:
                                domain = None

                            if counter > int(limit_result):
                                break
                            banner_dic = {
                                'ip': banner.get('ip', None),
                                'domain': domain,
                                'port': service.get('port', None),
                                'country': banner.get('location', {}).get('country_code', None),
                                'technology': technology,
                                'feed': 'censys',
                                'timestamp': banner.get('last_updated_at', None)
                            }
                            results.append(banner_dic)

                    page = banners['result']['links']['next']

                    if page:
                        data['cursor'] = page
                    else:
                        break

                if query_limit.lower() == "yes":
                    break

            return results
        except Exception as e:
            logging.error(f"ERROR censys search {e}")
        return results
