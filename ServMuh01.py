import sys
import socket
import select
import os
import time
import subprocess
import threading

class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"

HOST = ''
SOCKET_LIST = []
RECV_BUFFER = 4096
PORT = 9009
ROOM_CAPACITY = 3

users = {
    "user1": "1234",
    "user2": "1234",
    "user3": "1234"
}

users_sockets = {}
active_connections = {}

def initiate_sudo():
    subprocess.run("sudo clear", shell=True)

def log(message):
    print(f"[SERVER LOG] {time.strftime('%H:%M:%S')} - {message}")

def get_username(sock):
    for username, user_sock in users_sockets.items():
        if user_sock == sock:
            return username
    return "Unknown"

def disconnect_client(sock):
    log(Colors.YELLOW + "Dissconnect client initiated" + Colors.RESET)
    username = get_username(sock)
    if username != "Unknown":
        if username in users_sockets and users_sockets[username] == sock:
            del users_sockets[username]
            log(f"Removed {username} from users_sockets")
        
        if username in active_connections:
            del active_connections[username]
            
    if sock in SOCKET_LIST:
        SOCKET_LIST.remove(sock)
        log(f"Removed socket from SOCKET_LIST")
    try:
        sock.close()
    except:
        pass
    if username != "Unknown":
        # Broadcast without causing recursion
        for client_sock in SOCKET_LIST[:]:
            if client_sock != server_socket and client_sock != sock and client_sock.fileno() != -1:
                try:
                    client_sock.send((Colors.YELLOW + f"[{username}] is offline.\n" + Colors.RESET).encode())
                except:
                    pass
        log(f"{username} disconnected cleanly")

def broadcast(server_socket, sender_sock, message):
    log(Colors.YELLOW + "Broadcast initiated" + Colors.RESET)

    to_remove = []
    for client_sock in SOCKET_LIST[:]:
        if client_sock != server_socket and client_sock != sender_sock and client_sock.fileno() != -1:
            try:
                client_sock.send(message.encode())
            except:
                log(f"Error sending to client, marking for removal")
                to_remove.append(client_sock)
    
    # Remove faulty sockets after broadcast
    for sock in to_remove:
        if sock in SOCKET_LIST:
            SOCKET_LIST.remove(sock)
        try:
            sock.close()
        except:
            pass

def show_available_commands(sock):
    response = Colors.YELLOW + """\nAvailable commands:
    $$[commands] - List available commands
    $$[hsr]      - Hard server reset (RESTARTS the machine)
    $$[serversh] - Shutdown server computer
    $$[svicesh]  - Stop server service
    $$[sviceres] - Restart server service
    $$[ls]       - List connected users
    $$[quit]     - Disconnect from server
    """ + Colors.RESET
    try:
        sock.send(response.encode())
    except:
        pass

def hard_server_reset(sock):
    try:
        sock.send((Colors.RED + "\nRESTARTING SERVER COMPUTER IN 10 SECONDS..." + Colors.RESET).encode())
    except:
        pass
    log("Server restart initiated by user.")
    time.sleep(10)
    os.system("reboot")

def server_shutdown(sock):
    try:
        sock.send((Colors.RED + "\nSERVER SHUTTING DOWN IN 15 SECONDS..." + Colors.RESET).encode())
    except:
        pass
    log("Server shutdown initiated by user.")
    time.sleep(15)
    os.system("shutdown now")

def server_service_shutdown(sock):
    try:
        sock.send((Colors.RED + "\nStopping server service in 5 seconds..." + Colors.RESET).encode())
    except:
        pass
    log("Server service shutdown initiated.")
    time.sleep(5)
    os._exit(1)

def restart_server_service():
    log("Restarting server service...")
    os.execv(sys.executable, ['python'] + [sys.argv[0]])

def server_service_restart(sock):
    try:
        sock.send((Colors.MAGENTA + "\nRestarting server service in 3 seconds..." + Colors.RESET).encode())
    except:
        pass
    
    # Broadcast without causing errors
    for client_sock in SOCKET_LIST[:]:
        if client_sock != server_socket and client_sock != sock and client_sock.fileno() != -1:
            try:
                client_sock.send(Colors.MAGENTA + "\nSERVER IS RESTARTING! Reconnect in a moment..." + Colors.RESET)
            except:
                pass
    
    time.sleep(3)
    threading.Thread(target=restart_server_service).start()
    os._exit(0)

def quit_command(sock):
    username = get_username(sock)
    try:
        sock.send((Colors.YELLOW + "Goodbye!\n" + Colors.RESET).encode())
    except:
        pass
    disconnect_client(sock)

def unknown_command(sock):
    try:
        sock.send((Colors.RED + "Unknown command. Use $$[commands] for help.\n" + Colors.RESET).encode())
    except:
        pass

def list_connected_users(sock):
    user_list = "\n--- Connected Users ---\n"
    for username in users_sockets:
        user_list += f"- {username}\n"
    user_list += f"Total: {len(users_sockets)}/{ROOM_CAPACITY}\n"
    user_list += "------------------------\n"
    try:
        sock.send((Colors.GREEN + user_list + Colors.RESET).encode())
    except:
        pass

def process_command(command, sock):
    log(Colors.YELLOW + f"Command process initiated." + Colors.RESET)
    username = get_username(sock)
    if not command:
        try:
            sock.send((Colors.RED + "Empty command.\n" + Colors.RESET).encode())
        except:
            pass
        return

    log(f"{username} issued command: $$[{command}]")
    
    command_handlers = {
        "commands": show_available_commands,
        "hsr": hard_server_reset,
        "serversh": server_shutdown,
        "svicesh": server_service_shutdown,
        "sviceres": server_service_restart,
        "ls": list_connected_users,
        "quit": quit_command,
    }
    
    handler = command_handlers.get(command, unknown_command)
    handler(sock)

def authenticate(sock):
    log(Colors.YELLOW + "Autentication process initiated." + Colors.RESET)

    try:
        sock.send("Enter username: ".encode())
        username = sock.recv(RECV_BUFFER).decode().strip()
        sock.send("Enter password: ".encode())
        password = sock.recv(RECV_BUFFER).decode().strip()
    except:
        try:
            sock.close()
        except:
            pass
        return None

    if username in users and users[username] == password:
        if username in users_sockets:
            old_sock = users_sockets[username]
            if old_sock != sock:
                log(f"Duplicate login detected for {username}")
                # Disconnect old client
                try:
                    old_sock.send(Colors.RED + "\nAnother session has logged in with your credentials. Disconnecting...\n" + Colors.RESET)
                except:
                    pass
                try:
                    old_sock.close()
                except:
                    pass
                
                # Clean up old connection
                if old_sock in SOCKET_LIST:
                    SOCKET_LIST.remove(old_sock)
                if username in users_sockets:
                    del users_sockets[username]
                if username in active_connections:
                    del active_connections[username]
        
        active_connections[username] = time.time()
        users_sockets[username] = sock
        
        log(f"{username} authenticated successfully")
        
        welcome_msg = Colors.GREEN + f"\nAuthentication successful! Connected to server.\n"
        welcome_msg += f"Server info: {HOST}:{PORT}\n"
        welcome_msg += f"Room capacity: {ROOM_CAPACITY} users\n"
        welcome_msg += f"Active users: {len(users_sockets)}\n" + Colors.RESET
        try:
            sock.send(welcome_msg.encode())
        except:
            pass
        
        return username

    else:
        try:
            sock.send("Authentication failed. Disconnecting...\n".encode())
        except:
            pass
        try:
            sock.close()
        except:
            pass
        return None

def chat_server():

    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    SOCKET_LIST.append(server_socket)
    log("Socket server process initiated.")
    log(f"Chat server started on port {PORT}")

    while True:
        try:
            read_ready, _, _ = select.select(SOCKET_LIST, [], [], 0.1)
        except Exception as e:
            log(f"Select error: {e}")
            continue

        for sock in read_ready:
            if sock == server_socket:
                try:
                    client_sock, addr = server_socket.accept()
                    client_sock.setblocking(True)
                    log(f"Connection attempt from {addr}")
                    if len(users_sockets) < ROOM_CAPACITY:
                        username = authenticate(client_sock)
                        if username:
                            SOCKET_LIST.append(client_sock)
                            # Broadcast join message
                            for client in SOCKET_LIST[:]:
                                if client != server_socket and client != client_sock and client.fileno() != -1:
                                    try:
                                        client.send(Colors.BLUE + f"[{username}] joined the chat\n" + Colors.RESET)
                                    except:
                                        pass
                        else:
                            try:
                                client_sock.close()
                            except:
                                pass
                    else:
                        try:
                            client_sock.send("Room is full. Disconnecting...".encode())
                        except:
                            pass
                        try:
                            client_sock.close()
                        except:
                            pass
                except Exception as e:
                    log(f"Accept error: {e}")
            else:
                try:
                    data = sock.recv(RECV_BUFFER)
                    if data:
                        message = data.decode('utf-8', errors="replace").strip()
                        if message.startswith("$$[") and message.endswith("]"):

                            command = message[3:-1].strip().lower()
                            process_command(command, sock)
                        else:
                            username = get_username(sock)
                            log(f"{username} says: {message}")
                            # Broadcast message
                            for client in SOCKET_LIST[:]:
                                if client != server_socket and client != sock and client.fileno() != -1:
                                    try:
                                        client.send(f"[{username}] {message}\n".encode())
                                    except:
                                        pass
                    else:
                        disconnect_client(sock)
                except (ConnectionResetError, BrokenPipeError, OSError) as e:
                    log(f"Socket error: {e}")
                    disconnect_client(sock)
                except Exception as e:
                    log(f"Unexpected error with client socket: {e}")
                    disconnect_client(sock)

    server_socket.close()
    
if __name__ == "__main__":
    initiate_sudo()
    chat_server()