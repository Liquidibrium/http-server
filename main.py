import socket
import threading
import traceback
import RequestHandler
import data
server_sockets = []

# server creates class insance HTTP Request Handler,
# which handles clinet request and sends apropriate response
# if error is occure client_socket will be closed
def handle_http_request(client_socket, address):
    try:
        handeler = RequestHandler.HTTPRequestHandler(client_socket, address)
        while True:
            message = client_socket.recv(data.CLIENT_MAX_MESSAGE_SIZE).decode()
            if not message:
                client_socket.close()
                return
            if not handeler.handle(message):
                return
    except Exception as exc:
        print(f'exception happened : {exc}\nclosing client socket')
        client_socket.close()

# accept connection with clients,
# handle messages from them in new thread
def get_clients(server_socket, address):
    try:
        while True:
            client_socket, address = server_socket.accept()
            thread = threading.Thread(
                target=handle_http_request, args=(client_socket, address))
            thread.start()
    except Exception:
        server_socket.close()
        print('catched KeyboardInterrupt, closing server socket')


def open_sockets(server_address):
    # TCP server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(server_address)
    # number of parallel connections to wait for accept
    server_socket.listen(data.PARALELL_CONN)
    return server_socket


def close_sever_sockets():
    for socket in server_sockets:
        socket.close()

# start unique ip:port  sockets
# in new thread to process clients requests
def start_severs():
    ip_port_dict = data.get_unique_addresses()
    for ip in ip_port_dict.keys():
        for port in ip_port_dict[ip]:
            server_address = (ip, port)
            socket = open_sockets(server_address)
            server_sockets.append(socket)
            thread = threading.Thread(
                target=get_clients, args=(socket, server_address))
            thread.start()
    print("All servers are ready ")


# starts main process
# servers are going to work forever unless Exceprion happens
try:
    start_severs()
except Exception as exc:
    traceback.print_exc()
    close_sever_sockets()
