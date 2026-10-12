import socket
import threading
import subprocess
import ssl

class KenRyxKatana:
    def __init__(self, host='127.0.0.1', port=55555):
        self.host = host
        self.port = port
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(certfile="server.crt", keyfile="server.key")

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"Server started at {self.host}:{self.port}")

        while True:
            client, address = server.accept()
            ssl_client = self.context.wrap_socket(client, server_side=True)
            print(f"Accepted connection from {address}")
            thread = threading.Thread(target=self.handle_client, args=(ssl_client,))
            thread.start()

    def handle_client(self, client):
        while True:
            command = client.recv(1024).decode('ascii')
            if command.startswith("upload"):
                self.receive_file(client, command[7:])
            elif command.startswith("download"):
                self.send_file(client, command[9:])
            elif command:
                output = subprocess.getoutput(command)
                client.sendall(output.encode('ascii'))

    def receive_file(self, client, filename):
        with open(filename, 'wb') as file:
            while True:
                data = client.recv(4096)
                if not data:
                    break
                file.write(data)

    def send_file(self, client, filename):
        with open(filename, 'rb') as file:
            data = file.read()
            client.sendall(data)

    def start_client(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_ssl = self.context.wrap_socket(client)
        client_ssl.connect((self.host, self.port))
        print(f"Connected to server at {self.host}:{self.port}")

        while True:
            command = input('>')
            client_ssl.send(command.encode('ascii'))
            if command.startswith("upload"):
                self.send_file(client_ssl, command[7:])
            elif command.startswith("download"):
                self.receive_file(client_ssl, command[9:])
            else:
                response = client_ssl.recv(4096).decode('ascii')
                print(response)

if __name__ == "__main__":
    tool = KenRyxKatana()
    choice = input("Start as (s)erver or (c)lient?")
    if choice == 's':
        tool.start_server()
    elif choice == 'c':
        tool.start_client()
