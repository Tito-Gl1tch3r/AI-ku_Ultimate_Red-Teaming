import requests
import yaml
import os
import sys

VULNERS_API_URL = 'https://vulners.com/api/v3/burp/software/'

API_KEY = os.getenv('VULNERS_API_KEY')

current_dir = os.path.dirname(os.path.abspath(__file__))
path_to_vulnerability_intels = os.path.join(current_dir, "..", "exposor", "intels", "vulnerability_intels")


def get_cpe_from_yaml(yaml_file):
    """
    Extract the CPE from the YAML file.
    The YAML file should have a field like 'cpe: cpe:/a:microsoft:office'.
    """
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
        print(data)
        if 'cpe' in data['info']:
            return data['info']['cpe']
        else:
            raise ValueError('CPE not found in the YAML file.')

def get_cves_for_cpe(cpe):
    """
    Send the extracted CPE to Vulners API and get the list of CVEs.
    """

    headers = {
        'Content-Type': 'application/json',
        'X-Vulners-Api-Key': API_KEY
    }
    query = {
        'software': f'{cpe}'
    }

    response = requests.post(VULNERS_API_URL, json=query, headers=headers)
    if response.status_code == 200:
        return response.json().get('data', {}).get('search', [])
    else:
        raise Exception(f"Error querying Vulners API: {response.status_code} - {response.text}")


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(IndentDumper, self).increase_indent(flow, False)


def save_cves_to_yaml(cpe, cves, output_folder = path_to_vulnerability_intels):
    cpe_parts = cpe.split(":") 
    vendor = cpe_parts[3]
    product = cpe_parts[4]
    filename = vendor + "_" + product + "_cves" + ".yaml"
    output_path = os.path.join(output_folder, filename)
    data = {
        'cpe': cpe,
        'total_cves': len(cves),
        'cves': sorted(list(cves))
    }
    os.makedirs(output_folder, exist_ok=True)
    with open(output_path, 'w') as f:
        yaml.dump(data, f, Dumper=IndentDumper)
    print(f"Saved CVEs to {output_path}")


def main(yaml_file):
    print(yaml_file)
    yaml_directory = 'technology_intels/'
    results = []
    try:
        # Extract the CPE from the YAML file
        cpe = get_cpe_from_yaml(yaml_file)
        print(f"Extracted CPE: {cpe}")

        # Get the list of CVEs affecting the given CPE
        cves = get_cves_for_cpe(cpe)

        if cves:

            print(f"Found {len(cves)} CVEs for the given CPE:")

            for warn in cves:
               item = {
                'Title': warn.get('_source').get('title'),
                'Score': warn.get('_source').get('cvss').get('score'),
                'External_url': warn.get('_source').get('href'),
                'CVE': warn.get('_source').get('id'),
                'cvelist': warn.get('_source').get('cvelist'),
                'ID': warn.get('_id'),
                'Published': warn.get('_source').get('published'),
                'Source': "https://vulners.com/cve/" + warn.get('_id'),
                'Warning': 'Info',}
               results.append(item)
            unique_cves = set()
            for item in results:
                cve_value = item.get('cvelist')
                if isinstance(cve_value, list):
                    unique_cves.update(cve_value)
                elif isinstance(cve_value, str):
                    unique_cves.add(cve_value)
            unique_cves = list(unique_cves)
            print("Unique CVEs:", unique_cves)
            print(len(unique_cves))
            save_cves_to_yaml(cpe, unique_cves)
        else:
            print("No CVEs found for the given CPE.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    yaml_file = sys.argv[1]
    main(yaml_file)
