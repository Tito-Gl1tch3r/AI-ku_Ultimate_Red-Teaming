#!./bin/python3

import sys
import os
import base64
from pyovpn_as import client
import pyovpn_as.api.exceptions
import argparse



# decoding stub
def decode_pass(encoded_string):
	decoded_bytes = base64.b64decode(encoded_string)
	decoded_string = decoded_bytes.decode("ascii")
	return decoded_string



parser = argparse.ArgumentParser()
try: 
	parser.add_argument('-H', '--host', dest = 'host', default = None,
						help = 'Hostname of target OpenVPN endpoint')
	parser.add_argument('-p', '--port', dest = 'port', default = '443',
						help = "Specify XMLRPC server API port, default is 443")
	parser.add_argument('-u', '--user', dest = 'user', default = 'openvpn_as',
						help = "Specify username for authentication")
	parser.add_argument('-P', '--pass', dest = 'pw', default = None,
						help = 'Specify user password for authentication in base64 encoded format.')
	parser.add_argument('-A','--add-user', action = "store_true", dest = 'adduser', default = False,
						help = 'Specify whether or not an attempt to add a user to the OVPN server should be attempted via XMLRPC.  Defaults to False' )
	parser.add_argument('-c', '--command', dest = 'cmd', default = None,
						help = 'Specify command to be executed by XMLRPC, options are "adduser", "deluser" and "foo".' )
	parser.add_argument('-d', '--debug', dest = 'debug', action = 'store_true', default = False,
						help = "Prints debug messages.")
	args = parser.parse_args()
except KeyboardInterrupt:
	# handle exit() from passing --help
	raise
def _exit(code):
	print(FG_RST + ST_RST, end='')
	sys.exit(code)

if args.debug:
	os.environ['WDM_LOG_LEVEL'] = '4'

if args.host is None:
	print ('Hostname value is required.  Please run again with -H flag and hostname argument specified!')
	sys.exit(1)

if args.cmd is None:
	print('Command is a needed argument. Please specify a command with "-c" or "--command".  For command options see help command or documentation README.')
	sys.exit(1)

if args.cmd == 'adduser':
	try:
		rawpass = args.pw
		pw_bytes = str.encode(rawpass)
		pw = decode_pass(pw_bytes)
		mgmt_client = client.from_args('https://' + args.host + ':' + args.port + '/RPC2/', args.user, pw, allow_untrusted = True )
		new_user = mgmt_client.users.create_new_user('newuser', 'p0pp1nsh3lls', prop_superuser=True)

	except pyovpn_as.api.exceptions.ApiCientAuthError:
	# once upstream PR is merged to correct typo in exceptions.py delete lines 68 and 69 and uncomment 70
	#except pyovpn_as.api.exceptions.ApiCientAuthError: 
		print('XMLRPCRelay: AUTH_FAILED: Server Agent XML-RPC method requires admin-level access when called externally')



if args.cmd == 'deluser':
	try:

		mgmt_client = client.from_args('https://' + args.host + ':' + args.port + '/RPC2/', args.user, pw, allow_untrusted = True )
		mgmt_client.users.delete_user(as_client, '')
	except pyonvpn_as.api.exceptions.AccessServerProfileNotFound:
		print (f'User {args.user} Does not exist! Unable to delete.')
	except pyonvpn_as.api.exceptions.AccessServerProfileExistsError:
		print (f' User {args.user} is a group profile! Unable to delete.')
	except pyonvpn_as.api.exceptions.AccessServerProfileDeleteError:
		print (f'Unable to delete user {args.user}! An unknown error occurred!')
	else:
		print (f'User {args.user} deleted successfully')



if args.cmd is None:
	print('No XMLRPC command specified!')
	sys.exit(1)



