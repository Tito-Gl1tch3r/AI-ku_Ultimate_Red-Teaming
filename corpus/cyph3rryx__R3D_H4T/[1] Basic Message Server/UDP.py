import socket

def start_server():
    host = '127.0.0.1'   # Localhost
    port = 12345        # Arbitrary non-privileged port

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

    # Bind socket to local host and port
    server_socket.bind((host, port))

    print('UDP Server started on {0}:{1}'.format(host, port))

    while True:
        data, addr = server_socket.recvfrom(1024)
        print('Received ', repr(data), 'From', addr)

if __name__ == "__main__":
    start_server()
