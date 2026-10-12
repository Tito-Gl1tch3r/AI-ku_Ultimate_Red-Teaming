import argparse
import ipaddress
import json
import logging
import os
import re
import textwrap

from dotenv import load_dotenv


class CustomHelpFormatter(argparse.HelpFormatter):
    def _format_action(self, action):
        option_string = ", ".join(action.option_strings)
        help_text = self._expand_help(action)
        max_width = 110
        indent = 26
        help_lines = textwrap.wrap(help_text, width=max_width - indent)
        if help_lines:
            first_line = f"{option_string:<25} {help_lines[0]}"
            subsequent_lines = "\n".join(f"{' ' * 26}{line}" for line in help_lines[1:])
            return f"{first_line}\n{subsequent_lines}\n" if subsequent_lines else f"{first_line}\n"
        else:
            return f"{option_string:<25}\n"


class RegexValidator(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # Format checker of CPE input
        cpe_pattern = r"^cpe:2\.3:[aho]:([a-zA-Z0-9\-\_\.]+):([a-zA-Z0-9\-\_\.]+)(:([a-zA-Z0-9\-\_\*]+))?(:([a-zA-Z0-9\-\_\*]+))?(:([a-zA-Z0-9\-\_\*]+))?(:([a-zA-Z0-9\-\_\*]+))?(:([a-zA-Z0-9\-\_\*]+))?(:([a-zA-Z0-9\-\_\*]+))?(:([a-zA-Z0-9\-\_\*]+))?(:([a-zA-Z0-9\-\_\*]+))?$"
        # Format checker of CVE input
        cve_pattern = r"^CVE-\d{4}-\d{4,7}$"

        if re.match(cpe_pattern, values):
            setattr(namespace, self.dest, values)
            namespace.query_type = "CPE"
        elif re.match(cve_pattern, values):
            setattr(namespace, self.dest, values)
            namespace.query_type = "CVE"
        else:
            parser.error(f"Invalid format: {values}. Expected format for CPE: 'cpe:2.3:a:vendor:product', or for CVE: 'CVE-YYYY-XXXX'.")


def configure():
    load_dotenv(override=True)


def get_api_keys():
    configure()
    print("READ .env file content")


def init_feed_api_keys(init_args, parser):
    API_KEYS_STRUCTURE = {
        "shodan": ["api_key"],
        "censys": ["api_id", "api_key"],
        "fofa": ["email", "api_key"],
        "zoomeye": ["api_key"]
    }
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    env_file_path = os.path.join(project_root, ".env")
    env_content = {}
    if os.path.exists(env_file_path):
        with open(env_file_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    env_content[key] = value
    for arg in init_args:
        parts = arg.split(":")
        feed = parts[0]

        # check if feed is valide
        if feed not in API_KEYS_STRUCTURE:
            parser.error(f"invalid feed: {feed}. Supported feeds are {', '.join(API_KEYS_STRUCTURE.keys())}")
            continue

        expected_fields = API_KEYS_STRUCTURE[feed]
        if len(parts[1:]) != len(expected_fields):
            parser.error(f"Invalid format for {feed}. Expected format: {feed}:{':'.join(expected_fields)}")
            continue

        for i, field in enumerate(expected_fields):
            env_var_name = f"{feed.upper()}_{field.upper()}"
            env_content[env_var_name] = parts[i + 1]

    with open(env_file_path, "w") as file:
        for key, value in env_content.items():
            file.write(f"{key}={value}\n")
    logging.info(f"{env_file_path} has been created/updated with the specified API keys.")


def validate_args(args, parser):
    if 'all' in args.feed and len(args.feed) > 1:
        parser.error("Invalid combination: '--feed all' cannot be combined with other feed options.")
        return 0


def check_api_keys(feed_args, parser):
    configure()
    logging.info("Checking if API key exists...")
    API_KEYS_STRUCTURE = {
        "shodan": ["api_key"],
        "censys": ["api_id", "api_key"],
        "fofa": ["email", "api_key"],
        "zoomeye": ["api_key"]
    }

    missing_keys = []
    feeds_to_check = API_KEYS_STRUCTURE.keys() if 'all' in feed_args else feed_args

    for feed in feeds_to_check:
        expected_fields = API_KEYS_STRUCTURE.get(feed, [])
        for field in expected_fields:
            env_var_name = f"{feed.upper()}_{field.upper()}"
            if not os.getenv(env_var_name):
                missing_keys.append(f"{feed}")

    if missing_keys:
        parser.error(f"Missing API keys for the following feeds: {missing_keys}")
        return False

    logging.info("All required API keys are present.")
    return True


def check_required_args(args, parser):
    if not (args.init or args.update):
        if not args.query:
            parser.error("The following argument is required: `-q` or `--query`")

    if args.init and (args.feed or args.query):
        parser.error("First initiate API keys")

    provided_args = [arg for arg in [args.country, args.netblock, args.domain_name] if arg is not None]

    if len(provided_args) > 1:
        parser.error("You must choose only one option: --country, --netblock, or --domain-name.")


def check_country_args(country_code, countries_file, parser):
    try:
        with open(countries_file, "r") as file:
            countries = json.load(file)
        for country in countries:
            if country["alpha-2"] == country_code.upper():
                logging.debug("You provided a valid country code.")
                return True
        return False

    except Exception as e:
        logging.error("An exception occured while reading the country codes JSON file: {e}")
        return False


def check_net_args(net, parser):
    try:
        ipaddress.ip_address(net)
        logging.debug("You provided a valid IP address.")
        return True
    except ValueError:
        try:
            ipaddress.ip_network(net, strict=False)
            logging.debug("You provided a valid CIDR..")
            return True
        except ValueError:
            return False


def check_domain_args(domain, parser):
    hostname_pattern = r"^([A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}$"
    if re.match(hostname_pattern, domain):
        return True
    else:
        return False
