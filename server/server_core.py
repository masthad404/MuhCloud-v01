import sys
import socket
import select
import os
import time
import subprocess
import threading
from shared.config import HOST, PORT, RECV_BUFFER, ROOM_CAPACITY, Colors, USERS
from server.logger import log, log_with_color
from server.user_manager import UserManager
from server.commands import CommandHandler

# Global variables
server_socket = None
shutdown_requested = False
SOCKET_LIST = []
user_manager = UserManager()

def set_shutdown_flag(value):
    global shutdown_requested
    shutdown_requested = value

def reset_server_state():
    global SOCKET_LIST, user_manager, shutdown_requested, server_socket
    user_manager.users_sockets.clear()
    user_manager.active_connections.clear()
    
    # Close all sockets
    for sock in SOCKET_LIST[:]:
        try:
            if sock.fileno() != -1:  # Only close valid sockets
                sock.close()
        except:
            pass
    SOCKET_LIST.clear()
    
    # Reset user manager
    user_manager.users_sockets.clear()
    user_manager.active_connections.clear()
    
    # Reset server socket
    if server_socket and server_socket.fileno() != -1:
        try:
            server_socket.close()
        except:
            pass
    server_socket = None
    
    # Reset shutdown flag
    shutdown_requested = False

def chat_server(user_manager=None):
    global server_socket, shutdown_requested, SOCKET_LIST
    if user_manager is None:
        user_manager = UserManager()
    # Reset state before starting
    reset_server_state()
    
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(10)
        server_socket.setblocking(True)  # Changed to blocking
        SOCKET_LIST.append(server_socket)
        log("Socket server process initiated.")
        log(f"Chat server started on port {PORT}")
    except OSError as e:
        log(f"Failed to start server: {e}")
        return

    # Initialize command handler
    command_handler = CommandHandler(user_manager, SOCKET_LIST, server_socket)

    while not shutdown_requested:
        try:
            # Use a timeout to check shutdown frequently
            read_ready, _, _ = select.select(SOCKET_LIST, [], [], 0.5)
        except Exception as e:
            if shutdown_requested:
                break
            log(f"Select error: {e}")
            continue

        for sock in read_ready:
            if shutdown_requested:
                break
                
            if sock == server_socket:
                try:
                    client_sock, addr = server_socket.accept()
                    client_sock.setblocking(True)
                    log(f"Connection attempt from {addr}")
                    
                    if len(user_manager.users_sockets) < ROOM_CAPACITY:
                        username, old_sock = user_manager.authenticate(client_sock)
                        if username:
                            # Handle duplicate login
                            if old_sock and old_sock in SOCKET_LIST:
                                try:
                                    old_sock.send(Colors.RED + "\nAnother session has logged in. Disconnecting...\n" + Colors.RESET)
                                except:
                                    pass
                                try:
                                    old_sock.close()
                                except:
                                    pass
                                if old_sock in SOCKET_LIST:
                                    SOCKET_LIST.remove(old_sock)
                            
                            SOCKET_LIST.append(client_sock)
                            # Broadcast join message
                            for client in SOCKET_LIST[:]:
                                if client != server_socket and client != client_sock and client.fileno() != -1:
                                    try:
                                        client.send((Colors.BLUE + f"[{username}] joined the chat\n" + Colors.RESET).encode())
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
                    if not shutdown_requested:
                        log(f"Accept error: {e}")
            else:
                try:
                    data = sock.recv(RECV_BUFFER)
                    if data:
                        message = data.decode('utf-8', errors="replace").strip()
                        if message.startswith("$$[") and message.endswith("]"):
                            command = message[3:-1].strip().lower()
                            
                            # Handle shutdown command
                            if command == "svicesh":
                                shutdown_requested = True
                                break
                                
                            command_handler.process_command(command, sock)
                        else:
                            username = user_manager.get_username(sock)
                            if username != "Unknown":
                                log(f"{username} says: {message}")
                                # Broadcast message
                                for client in SOCKET_LIST[:]:
                                    if client != server_socket and client != sock and client.fileno() != -1:
                                        try:
                                            client.send(f"[{username}] {message}\n".encode())
                                        except:
                                            pass
                    else:
                        # Client disconnected
                        username = user_manager.disconnect_client(sock)
                        if username:
                            # Broadcast disconnect message
                            for client in SOCKET_LIST[:]:
                                if client != server_socket and client != sock and client.fileno() != -1:
                                    try:
                                        client.send((Colors.YELLOW + f"[{username}] is offline.\n" + Colors.RESET).encode())
                                    except:
                                        pass
                        if sock in SOCKET_LIST:
                            SOCKET_LIST.remove(sock)
                        try:
                            sock.close()
                        except:
                            pass
                except (ConnectionResetError, BrokenPipeError, OSError) as e:
                    if not shutdown_requested:
                        log(f"Socket error: {e}")
                    username = user_manager.disconnect_client(sock)
                    if username:
                        for client in SOCKET_LIST[:]:
                            if client != server_socket and client != sock and client.fileno() != -1:
                                try:
                                    client.send((Colors.YELLOW + f"[{username}] is offline.\n" + Colors.RESET).encode())
                                except:
                                    pass
                    if sock in SOCKET_LIST:
                        SOCKET_LIST.remove(sock)
                    try:
                        sock.close()
                    except:
                        pass
                except Exception as e:
                    if not shutdown_requested:
                        log(f"Unexpected error with client socket: {e}")
                    username = user_manager.disconnect_client(sock)
                    if username:
                        for client in SOCKET_LIST[:]:
                            if client != server_socket and client != sock and client.fileno() != -1:
                                try:
                                    client.send((Colors.YELLOW + f"[{username}] is offline.\n" + Colors.RESET).encode())
                                except:
                                    pass
                    if sock in SOCKET_LIST:
                        SOCKET_LIST.remove(sock)
                    try:
                        sock.close()
                    except:
                        pass

    # Cleanup before exit
    log("Server shutting down...")
    for sock in SOCKET_LIST[:]:
        try:
            if sock.fileno() != -1:
                sock.close()
        except:
            pass
    SOCKET_LIST.clear()
    
    try:
        if server_socket and server_socket.fileno() != -1:
            server_socket.close()
    except:
        pass
    
    user_manager.users_sockets.clear()
    user_manager.active_connections.clear()