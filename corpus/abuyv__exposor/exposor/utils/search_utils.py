import os
import logging
import uuid
import yaml
from pathlib import Path


current_dir = os.path.dirname(os.path.abspath(__file__))
path_to_technology_intels = os.path.join(current_dir, "..", "intels", "technology_intels")
path_to_vulnerability_intels = os.path.join(current_dir, "..", "intels", "vulnerability_intels")

def find_technology_intel(user_cpe, folder_path = path_to_technology_intels):
    """Searches for a yaml file in the intels folder for a user input as CPE"""
    result = []
    cpe_parts = user_cpe.split(":") 
    vendor = cpe_parts[3]
    product = cpe_parts[4]
    technology_yaml_file = vendor + "_" + product + ".yaml"
    try:
        path_to_technology = os.path.join(folder_path, vendor, product, technology_yaml_file)
        # We get multiple queries for single CPE; Shodan might have more than 1 query; so You need to have a logic handling it.
        with open(path_to_technology, "r") as f:
            technology_intel = yaml.safe_load(f)
            #debugging of yaml content
            logging.debug(f"YAML file found of {technology_yaml_file} file: {technology_intel}")
            result.append(technology_intel) 
            return result
    except Exception as e:
        logging.debug(f"Failed to find a file {path_to_technology}")
        return None


def find_vulnerability_intel(user_cve, folder_path = path_to_vulnerability_intels):
    """Search for a yaml file in the intels folder for a user input as CVE"""
    contains = []
    result = []
    id_ = uuid.uuid4()
    for path in Path(folder_path).rglob('*.yaml'):
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                if user_cve in str(data):
                    logging.debug(f"CVE exists in {path} file") 
                    logging.debug(f"Content of Yaml file: {data}") 
                    contains.append(path)
                    logging.info(f"Extracted CPE: {data['cpe']}")
                    result.append(find_technology_intel(data['cpe']))
        except:
             pass
    if not contains:
        logging.warning(f"{user_cve} is not supported!")

    return result
