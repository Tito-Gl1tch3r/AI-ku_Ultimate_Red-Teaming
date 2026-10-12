import os
import logging
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from exposor.utils import args_helpers
from exposor.feeds.shodan.shodan_feed import Shodan
from exposor.feeds.zoomeye.zoomeye_feed import Zoomeye
from exposor.feeds.fofa.fofa_feed import Fofa
from exposor.feeds.censys.censys_feed import Censys

cpe = None
auth_status = {}
args_helpers.configure()
hashed_query = []
query_cache = {}
result_feed = []


def get_user_selected_queries(feed_dict, user_selected_feeds):
    if "all" in user_selected_feeds:
        return feed_dict
    return {feed: feed_dict.get(feed) for feed in user_selected_feeds if feed in feed_dict}


def authenticate_feed(feed):
    if auth_status.get(feed):
        return True
    if feed == "shodan":
        api_key = os.getenv("SHODAN_API_KEY")
        auth_status["shodan"] = Shodan.auth(api_key)
    elif feed == "zoomeye":
        api_key = os.getenv("ZOOMEYE_API_KEY")
        auth_status["zoomeye"] = Zoomeye.auth(api_key)
    elif feed == "censys":
        api_id = os.getenv("CENSYS_API_ID")
        secret = os.getenv("CENSYS_API_KEY")
        auth_status["censys"] = Censys.auth(api_id, secret)
    elif feed == "fofa":
        email = os.getenv("FOFA_EMAIL")
        api_id = os.getenv("FOFA_API_KEY")
        auth_status["fofa"] = Fofa.auth(email, api_id)
    return auth_status.get(feed, False)


def concurrent_doer(feed, query, args):
    if not authenticate_feed(feed):
        logging.error(f"Authentication failed for {feed}. Skipping query.")
        return

    logging.info(f"Sending {feed} request with query: {query}")

    if feed == "shodan":
        logging.debug("Sending query to Shodan...")
        results_shodan = Shodan.search(key=os.getenv("SHODAN_API_KEY"),queries=query, args = args, technology = cpe)
        result_feed.append(results_shodan)
    elif feed == "zoomeye":
        logging.debug("Sending query to Zoomeye...")
        results_zoomeye = Zoomeye.search(key=os.getenv("ZOOMEYE_API_KEY"),queries=query, args = args, technology = cpe)
        result_feed.append(results_zoomeye)
    elif feed == "fofa":
        logging.debug("Sending query to Fofa...")
        results_fofa = Fofa.search(email=os.getenv("FOFA_EMAIL"),key=os.getenv("FOFA_API_KEY"),queries=query, args = args, technology = cpe)
        result_feed.append(results_fofa)
    elif feed == "censys":
        logging.debug("Sending query to Censys...")
        results_censys = Censys.search(uid=os.getenv("CENSYS_API_ID"), key=os.getenv("CENSYS_API_KEY"),queries=query,args = args, technology = cpe)
        result_feed.append(results_censys)


def concurrent_query_processor(filtered_queries, args):
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(concurrent_doer, feed, query, args) for feed, query in filtered_queries.items()]
        for future in as_completed(futures):
            future.result()
    return 0


def query_parser_helper(entry, args):
    if (entry is None) or ("info" not in entry):
        return logging.debug(f"{entry} does not have necessary attributes.")
    info = entry.get('info', {})
    global cpe
    cpe = info.get('cpe')
    logging.info(f"Preparing queries for {cpe}")
    queries = entry.get('queries', {})
    filtered_queries = get_user_selected_queries(queries, args.feed)
    concurrent_query_processor(filtered_queries, args)


def query_parser(technology_files_content, args):
    feeds = []
    logging.debug(f"Content of technology files: {technology_files_content}")
    for index, item_list in enumerate(technology_files_content):
        if isinstance(item_list, list):
            for entry in item_list:
                query_parser_helper(entry, args)
        else:
            query_parser_helper(item_list, args)
    return result_feed
