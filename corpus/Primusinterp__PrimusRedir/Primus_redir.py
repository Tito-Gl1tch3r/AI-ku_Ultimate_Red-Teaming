#!/usr/bin/env python3
import os
import subprocess
import shutil
import textwrap
import re
from halo import Halo
import argparse
import sys
from rich.console import Console
from rich.table import Table
import time

# ─── CLI DEFINITION ────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description=(
        'PrimusRedir - Provision a C2 redirector on a VPS + WireGuard tunnel. '
        'Caddy is used as reverse proxy.'
    ),
    allow_abbrev=False  # Prevent abbreviations like -debug being interpreted as -d ebug
)
parser.add_argument('-d', type=str,
                    help='The domain & subdomain to listen on, e.g. foo.cooldomain.com')
parser.add_argument('--shutdown', action='store_true',
                    help='Tear down provisioned resources and shut down WireGuard')
parser.add_argument('--config', action='store_true',
                    help='Configure API keys for DigitalOcean & Cloudflare')
parser.add_argument('--debug', action='store_true',
                    help='Print live Terraform output and disable spinner')
parser.add_argument('--user-agent', type=str,
                    help='Custom User-Agent for C2 communication (default: Chrome 119)')
parser.add_argument('--c2-variant', type=str,
                    help='The C2 variant to use (e.g., standard, havoc - default: standard)')
parser.add_argument('--status', action='store_true',
                    help='Show redirector status and container logs')


if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

console = Console()

try:
    args = parser.parse_args()
except SystemExit:
    sys.exit(1)

# ─── SPINNER FACTORY ───────────────────────────────────────────────────────────
def load_spinner(operation="provisioning"):
    if args.debug:
        # dummy spinner: no-op start/stop
        class DummySpinner:
            def start(self): pass
            def stop(self):  pass
        return DummySpinner()
    
    spinner_text = {
        "provisioning": "Provisioning and configuring the redirector, please wait",
        "shutdown": "Tearing down resources, please wait"
    }.get(operation, "Please wait")
    
    return Halo(text=spinner_text, spinner='dots')

spinner = load_spinner()

# ─── TERRAFORM RUNNER ──────────────────────────────────────────────────────────
def run_terraform(cmd, operation="provisioning"):
    """
    Run a terraform command.
    - In debug mode: stream stdout/stderr live, return a fake CompletedProcess.
    - Otherwise: capture output, show spinner around it.
    """
    if args.debug:
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True)
        lines = []
        for line in proc.stdout:
            print(line, end='')
            lines.append(line)
        proc.wait()
        class R:
            def __init__(self, rc, out, err=""):
                self.returncode = rc
                self.stdout = out
                self.stderr = err
        return R(proc.returncode, ''.join(lines))
    else:
        spinner = load_spinner(operation)
        spinner.start()
        res = subprocess.run(cmd, text=True, capture_output=True)
        spinner.stop()
        return res

# ─── UTILITIES ────────────────────────────────────────────────────────────────
def patch_var(input_var, file_loc, patch_pattern):
    with open(file_loc) as f:
        content = f.read().replace(patch_pattern, input_var)
    with open(file_loc, 'w') as f:
        f.write(content)
    #print(f"{input_var} patched into {file_loc}")

def check_patch(file_loc, patch_pattern):
    with open(file_loc) as f:
        return patch_pattern in f.read()

def print_setup_summary(domain, redir_ip, user_agent):
    
    table = Table(title="PrimusRedir Setup Summary", show_header=True, header_style="bold magenta")
    
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Domain", domain)
    table.add_row("Redirector IP", redir_ip)
    table.add_row("WireGuard Interface", "wg0")
    table.add_row("WireGuard IP", "192.168.255.2/24")
    table.add_row("User-Agent", user_agent)
    table.add_row("Certificate Type", "Secure (Let's Encrypt via Caddy)")
    table.add_row("C2 Listener IP", "192.168.255.2")
    table.add_row("C2 Listener Port", "80")
    table.add_row("SSH to redirector:", f"sudo ssh -i ~/.ssh/primus_redir_id_rsa root@{redir_ip}")
    
    console.print(table)
    
    if not args.c2_variant or args.c2_variant == "standard":
        console.print("\n[bold yellow]Standard C2 Listener Configuration:[/bold yellow]")
        console.print("1. Set your C2 listener to: 192.168.255.2:80 (HTTP)")
        console.print(f"2. Use User-Agent: \"{user_agent}\" in your C2 configuration/profile.")
        console.print("\n[bold green]Setup complete! Your redirector is ready to use.[/bold green]")
    elif args.c2_variant == "havoc":
        console.print("\n[bold yellow]Havoc C2 Listener Configuration for Teamserver Profile:[/bold yellow]")
        console.print("Add the following listener configurations to your Havoc teamserver profile (e.g., havoc.yaotl):")

        listener1_for_implant_config = f"""
    
    # Implants will connect to: https://{domain}:443
    Http {{
        Name         = "External HTTPS ({domain})"  
        Hosts        = [ "{domain}" ]                 # Implant connects to this domain
        HostBind     = "192.168.255.2"               # Havoc C2 binds its listener to WG IP
        PortBind     = 443                         # Havoc C2 attempts to bind this port
        PortConn     = 443                         # Implant connects to this port on redirector
        HostRotation = "round-robin"
        Secure       = true                        # HTTPS listener
        UserAgent    = "{user_agent}"
        Uris         = [ "/api", "/login", "/config", "/admin", "/index.php" ] # Example URIs
    }}
        """

        listener2_c2_backend = f"""
    # This Http listener is the C2 server's actual backend for Caddy.
    # Caddy will forward traffic to this listener: http://192.168.255.2:80
    Http {{
        Name         = "Internal HTTP (C2 Backend)"  
        Hosts        = [ "192.168.255.2" ]           
        HostBind     = "192.168.255.2"               # C2 binds to WireGuard IP
        PortBind     = 80                            # C2 binds to this port
        PortConn     = 80                            
        HostRotation = "round-robin"
        Secure       = false                         # Http listener
        UserAgent    = "{user_agent}" 
        Uris         = [ "/api", "/login", "/config", "/admin", "/index.php" ] # Ensure these align with Caddy rules & above
    }}
        """
        
        console.print("\n[bold cyan]Listeners {[/bold cyan]")
        console.print(textwrap.indent(listener1_for_implant_config, "    "))
        console.print(textwrap.indent(listener2_c2_backend, "    "))
        console.print("[bold cyan]}[/bold cyan]")
        
        console.print("\n[bold yellow]Instructions for Havoc:[/bold yellow]")
        console.print("1. Ensure your Havoc C2 server starts both listeners defined above.")
        console.print("2. Generate your Havoc implants using the listener named: "
                      f"'[bold magenta]External HTTPS ({domain})[/bold magenta]'.")
        console.print("   This ensures implants connect to the redirector over HTTPS.")
        console.print("3. Caddy is configured to forward valid traffic to the "
                      "'[bold magenta]Internal HTTP (C2 Backend)[/bold magenta]' listener.")
        console.print(f"4. The User-Agent for both listeners in Havoc profile should be: \"{user_agent}\\")
        console.print("\n[bold green]Setup complete! Your redirector and Havoc guidance are ready.[/bold green]")
    else:
        console.print(f"\n[bold red]Unknown C2 variant: {args.c2_variant}. No specific C2 instructions provided.[/bold red]")

# ─── PATH CONSTANTS ───────────────────────────────────────────────────────────
old_cwd              = os.getcwd()
cwd                  = os.getcwd()
redir_folder         = f"{cwd}/redir"
tf_var_file_loc      = f"{cwd}/config_templates/variable.tf"
caddy_secure_loc     = f"{cwd}/config_templates/Caddyfile.secure.template"
tf_http_redir_loc    = f"{cwd}/config_templates/http_redir.tf"
tf_var_file_loc_new  = f"{cwd}/variable.tf"
caddy_loc_new        = f"{redir_folder}/Caddyfile"
tf_http_redir_loc_new= f"{cwd}/http_redir.tf"

# ─── MAIN OPERATIONS ──────────────────────────────────────────────────────────
def gen_conf():
    ssh_dir = os.path.expanduser("~/.ssh")
    ssh_priv_key_path = os.path.join(ssh_dir, "primus_redir_id_rsa") 
    ssh_pub_key_path = os.path.join(ssh_dir, "primus_redir_id_rsa.pub") 

    if not os.path.exists(ssh_priv_key_path):
        print(f"SSH private key not found at {ssh_priv_key_path}.")
        print("Generating a new SSH key pair for PrimusRedir...")
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        try:
            subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "4096", 
                            "-f", ssh_priv_key_path,  
                            "-N", "", "-C", "primusredir_vps_key"], 
                           check=True, capture_output=True, text=True)
            print(f"Successfully generated SSH key pair at {ssh_priv_key_path} and {ssh_pub_key_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error generating SSH key: {e.stderr}")
            sys.exit(1)
    else:
        print(f"Using existing PrimusRedir SSH private key: {ssh_priv_key_path}")

    if not os.path.exists(ssh_pub_key_path):
        print(f"Error: SSH public key {ssh_pub_key_path} not found, even after attempting generation.")
        print(f"Please ensure an SSH key pair can be created or exists at {ssh_priv_key_path} and {ssh_pub_key_path}")
        sys.exit(1)

    try:
        with open(ssh_pub_key_path, 'r') as f:
            public_key_content = f.read().strip()
    except IOError as e:
        print(f"Error reading SSH public key {ssh_pub_key_path}: {e}")
        sys.exit(1)

    if not os.path.exists(tf_var_file_loc):
        print("Error: missing config_templates/variable.tf")
        sys.exit(1)
    shutil.copy(tf_var_file_loc, cwd)
    
    if not os.path.exists(caddy_secure_loc):
        print(f"Error: missing {caddy_secure_loc}")
        sys.exit(1)
    shutil.copy(caddy_secure_loc, caddy_loc_new)
    
    shutil.copy(tf_http_redir_loc, cwd)

    dns_record       = args.d
    parts            = dns_record.split('.')
    sub_dns_record   = parts.pop(0)
    main_dns_record  = '.'.join(parts)

    # Simple domain validation
    if len(parts) < 1 or not sub_dns_record or not main_dns_record:
        print(f"Error: Invalid domain format '{dns_record}'. Expected format: subdomain.domain.com")
        print("Example: ost.coolsite.com")
        clean_up()
        sys.exit(1)

    # Get User-Agent
    user_agent = args.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.3"

    # patch Caddyfile
    patch_var(dns_record, caddy_loc_new, 'URL')
    patch_var(user_agent, caddy_loc_new, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.3')
    
    shutil.move(caddy_loc_new, f"{redir_folder}/Caddyfile")

    # patch Terraform http_redir.tf
    patch_var(main_dns_record, tf_http_redir_loc_new, 'DOMAIN')
    patch_var(sub_dns_record, tf_http_redir_loc_new, 'SUB')

    # generate WireGuard keys
    os.makedirs("keys", exist_ok=True)
    server_priv = subprocess.run(["wg", "genkey"],
                                 capture_output=True, text=True).stdout.strip()
    open("keys/server-privatekey", "w").write(server_priv)
    server_pub  = subprocess.run(["wg", "pubkey"],
                                 input=server_priv, capture_output=True, text=True).stdout.strip()
    open("keys/server-publickey", "w").write(server_pub)

    client_priv = subprocess.run(["wg", "genkey"],
                                 capture_output=True, text=True).stdout.strip()
    open("keys/client-privatekey", "w").write(client_priv)
    client_pub  = subprocess.run(["wg", "pubkey"],
                                 input=client_priv, capture_output=True, text=True).stdout.strip()
    open("keys/client-publickey", "w").write(client_pub)

    # patch TF variables
    patch_var(server_priv, tf_var_file_loc_new, 'SERVER-PRIVATE-KEY')
    patch_var(client_pub,     tf_var_file_loc_new, 'CLIENT-PUB-KEY')

    # Patch the SSH public key content into the new variable.tf
    patch_var(public_key_content, tf_var_file_loc_new, 'SSH-PUBLIC-KEY-CONTENT-PLACEHOLDER')

    # Terraform init & apply
    
    init_result = subprocess.run(["terraform", "init"], text=True, capture_output=True)
    if init_result.returncode != 0:
        print("Terraform init failed:")
        print("STDOUT:", init_result.stdout)
        print("STDERR:", init_result.stderr)
        clean_up()
        sys.exit(1)
        
    result = run_terraform(["terraform", "apply", "-auto-approve"], operation="provisioning")
    if result.returncode != 0:
        print("Terraform apply failed:")
        print("STDOUT:", result.stdout)
        if hasattr(result, 'stderr') and result.stderr:
            print("STDERR:", result.stderr)
        clean_up()
        sys.exit(1)

    m = re.search(
        r'droplet_ip_address\s*=\s*"(\d+\.\d+\.\d+\.\d+)"',
        result.stdout)
    redir_ip = m.group(1) if m else "<error in regex, please revise>"

    # Save VPS IP for status checks
    with open("vps_ip.txt", "w") as f:
        f.write(redir_ip)

    config = textwrap.dedent(f"""
        [Interface]
        PrivateKey = {client_priv}
        Address     = 192.168.255.2/24

        [Peer]
        PublicKey         = {server_pub}
        AllowedIPs        = 0.0.0.0/0
        Endpoint          = {redir_ip}:51820
        PersistentKeepalive = 25
    """).strip()

    print(config)
    with open("/etc/wireguard/wg0.conf", "w") as f:
        f.write(config)
    print("Config written to '/etc/wireguard/wg0.conf'")

    up = subprocess.run(['wg-quick', 'up', 'wg0'], text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Tunnel started" if up.returncode==0 else "Tunnel start failed")
    ping = subprocess.run(['ping', '-c', '4', redir_ip], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Connection OK" if ping.returncode==0 else "Ping test failed")

    print_setup_summary(
        domain=args.d,
        redir_ip=redir_ip,
        user_agent=user_agent
    )

def config():
    print("""Before we start, please ensure you have:
      - DigitalOcean & Cloudflare accounts
      - A domain on Cloudflare
      - API keys for both
    """)
    if check_patch(tf_var_file_loc, 'CLOUDFLARE-API-KEY'):
        cf_key = input("Cloudflare API key: ")
        patch_var(cf_key, tf_var_file_loc, 'CLOUDFLARE-API-KEY')
    if check_patch(tf_var_file_loc, 'DO-API-KEY'):
        do_key = input("DigitalOcean API key: ")
        patch_var(do_key, tf_var_file_loc, 'DO-API-KEY')
    print("Configuration complete.")

def clean_up():
    # Stop WireGuard tunnel FIRST to close all connections
    print("Stopping WireGuard tunnel to close all connections...")
    wg_check = subprocess.run(['wg', 'show', 'wg0'], 
                             capture_output=True, text=True)
    if wg_check.returncode == 0:
        down = subprocess.run(['wg-quick', 'down', 'wg0'], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Tunnel stopped" if down.returncode==0 else "Tunnel stop failed")
    else:
        print("No WireGuard tunnel to stop")
    
    # Give the tunnel a moment to fully close
    time.sleep(2)
    
    print("Running Terraform destroy...")
    result = run_terraform(["terraform", "destroy", "-auto-approve"], operation="shutdown")
    if result.returncode != 0:
        print("Terraform destroy failed:")
        print("STDOUT:", result.stdout)
        if hasattr(result, 'stderr') and result.stderr:
            print("STDERR:", result.stderr)

    # Check if WireGuard tunnel exists before trying to stop it
    wg_check = subprocess.run(['wg', 'show', 'wg0'], 
                             capture_output=True, text=True)
    if wg_check.returncode == 0:
        down = subprocess.run(['wg-quick', 'down', 'wg0'], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Tunnel stopped" if down.returncode==0 else "Tunnel stop failed")
    else:
        print("No WireGuard tunnel to stop")

    for fn in ("keys/server-privatekey","keys/server-publickey",
               "keys/client-privatekey","keys/client-publickey",
               "variable.tf", "http_redir.tf", "redir/Caddyfile",
               ".terraform.lock.hcl", "terraform.tfstate", "terraform.tfstate.backup",
               "vps_ip.txt"):
        try: os.remove(fn)
        except: pass

    print("Clean up complete.")

def get_status():
    """Get and display redirector status and container logs"""
    # Read VPS IP from saved file
    try:
        with open("vps_ip.txt", "r") as f:
            vps_ip = f.read().strip()
    except FileNotFoundError:
        console.print("[bold red]VPS IP not found. Has the redirector been provisioned?[/bold red]")
        return
    
    # Check if SSH key exists
    ssh_key = os.path.expanduser("~/.ssh/primus_redir_id_rsa")
    if not os.path.exists(ssh_key):
        console.print("[bold red]SSH key not found. Has the redirector been provisioned?[/bold red]")
        return
    
    console.print(f"\n[bold cyan]Checking redirector status on {vps_ip}...[/bold cyan]")
    
    # Check local WireGuard status
    wg_status = subprocess.run(['wg', 'show', 'wg0'], 
                              capture_output=True, text=True)
    wg_running = wg_status.returncode == 0
    
    # Check ping to VPS
    ping_result = subprocess.run(['ping', '-c', '3', '-W', '5', vps_ip], 
                                capture_output=True, text=True)
    ping_ok = ping_result.returncode == 0
    
    # SSH commands to get remote status
    ssh_cmd_base = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{vps_ip}"
    
    # Get container status
    docker_ps_cmd = f"{ssh_cmd_base} 'docker ps --format \"table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}\"'"
    docker_ps_result = subprocess.run(docker_ps_cmd, shell=True, capture_output=True, text=True)
    
    # Find the actual container name
    container_name = "redir_caddy_1"  # default
    if docker_ps_result.returncode == 0:
        for line in docker_ps_result.stdout.split('\n'):
            if 'caddy' in line.lower():
                parts = line.split('\t')
                if len(parts) > 0:
                    container_name = parts[0].strip()
                    # Clean up the container name (remove any extra whitespace or characters)
                    container_name = container_name.split()[0] if container_name else "redir_caddy_1"
                    break
    
    # Check Caddy configuration
    caddy_status = "🟡 UNKNOWN"
    caddy_details = "Could not check Caddy configuration"
    
    try:
        # First check if Caddy configuration is valid
        cert_check_cmd = f"{ssh_cmd_base} 'docker exec {container_name} caddy validate --config /etc/caddy/Caddyfile 2>&1 || echo \"Config validation failed\"'"
        cert_result = subprocess.run(cert_check_cmd, shell=True, capture_output=True, text=True)
        
        if cert_result.returncode == 0 and "valid" in cert_result.stdout.lower():
            caddy_status = "🟢 VALID"
            caddy_details = "Caddy configuration is valid"
        elif "error" in cert_result.stdout.lower() or "failed" in cert_result.stdout.lower():
            caddy_status = "🔴 ERROR"
            caddy_details = "Configuration has errors"
        else:
            # Try to get domain configuration as fallback
            caddyfile_check_cmd = f"{ssh_cmd_base} 'docker exec {container_name} cat /etc/caddy/Caddyfile | head -1 | tr -d \"{{\" | tr -d \"}}\"'"
            domain_result = subprocess.run(caddyfile_check_cmd, shell=True, capture_output=True, text=True)
            if domain_result.returncode == 0 and domain_result.stdout.strip():
                domain_to_check = domain_result.stdout.strip()
                config_check_cmd = f"{ssh_cmd_base} 'docker exec {container_name} cat /etc/caddy/Caddyfile | grep -q \"{domain_to_check}\" && echo \"Domain configured\" || echo \"Domain not found\"'"
                config_result = subprocess.run(config_check_cmd, shell=True, capture_output=True, text=True)
                
                if config_result.returncode == 0 and "Domain configured" in config_result.stdout:
                    caddy_status = "🟢 CONFIGURED"
                    caddy_details = f"Domain {domain_to_check} properly configured in Caddy"
                else:
                    caddy_status = "🟡 UNKNOWN"
                    caddy_details = f"Could not verify domain {domain_to_check} configuration"
    except:
        caddy_status = "🟡 UNKNOWN"
        caddy_details = "Could not check Caddy configuration"
    
    # Display status table
    status_table = Table(title="PrimusRedir Status", show_header=True, header_style="bold magenta")
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="green")
    status_table.add_column("Details", style="white")
    
    # Local network status
    status_table.add_row("WireGuard Tunnel", 
                        "🟢 UP" if wg_running else "🔴 DOWN",
                        "wg0 interface" if wg_running else "Interface not found")
    
    status_table.add_row("VPS Connectivity", 
                        "🟢 OK" if ping_ok else "🔴 FAILED",
                        f"Ping to {vps_ip}" if ping_ok else "Cannot reach VPS")
    
    # Container status
    if docker_ps_result.returncode == 0 and ("redir_caddy_1" in docker_ps_result.stdout or "caddy" in docker_ps_result.stdout):
        container_running = True
        container_info = docker_ps_result.stdout.strip().split('\n')[1]  # Skip header
        status_table.add_row("Caddy Container", "🟢 RUNNING", container_info)
    else:
        container_running = False
        status_table.add_row("Caddy Container", "🔴 STOPPED", "Container not found or not running")
    
    # Caddy configuration status
    status_table.add_row("Caddy Configuration", caddy_status, caddy_details)
    
    console.print(status_table)
    
    # SSH command for debugging
    ssh_command = f"sudo ssh -i ~/.ssh/primus_redir_id_rsa root@{vps_ip}"
    console.print(f"\n[bold cyan]SSH to redirector for debugging:[/bold cyan]")
    console.print(f"[bold green]{ssh_command}[/bold green]")
    
    # Overall status summary
    if wg_running and ping_ok and container_running:
        console.print("\n[bold green]✅ Redirector is healthy and operational![/bold green]")
    else:
        console.print("\n[bold red]❌ Redirector has issues that need attention[/bold red]")

# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    if args.status:
        get_status()
    elif args.shutdown:
        clean_up()
        print("Redirector shut down.")
    elif args.config:
        config()
    elif args.d:
        with open(tf_var_file_loc, 'r') as f:
            content = f.read()

        if 'CLOUDFLARE-API-KEY' and 'DO-API-KEY' in content:
            console.print("[bold red][WARNING] Cloudflare and DigitalOcean API keys have not been configured yet. Please run 'python3 Primus_redir.py --config' to configure them.[/bold red]")
            sys.exit(1)
        else:
            gen_conf()


