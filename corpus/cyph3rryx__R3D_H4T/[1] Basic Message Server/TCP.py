import socket

def start_server():
    host = '127.0.0.1' # Localhost
    port = 12345        # Arbitrary non-privileged port

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 

    # Bind socket to local host and port
    server_socket.bind((host, port))

    # Start listening on socket
    server_socket.listen(1)

    print('TCP Server started on {0}:{1}'.format(host, port))

    connection, address = server_socket.accept()

    print('Connected by', address)

    while True:
        data = connection.recv(1024)
        if not data:
            break
        print('Received ', repr(data))

    # close connection
    connection.close()

if __name__ == "__main__":
    start_server()
