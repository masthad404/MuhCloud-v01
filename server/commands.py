# server/commands.py
import os
import sys
import time
import threading
import subprocess
from server.logger import log, log_with_color
from shared.config import Colors, USERS, ROOM_CAPACITY
from server.user_manager import UserManager

class CommandHandler:
    def __init__(self, user_manager, socket_list, server_socket):
        self.user_manager = user_manager
        self.socket_list = socket_list
        self.server_socket = server_socket
        
        self.command_handlers = {
            "commands": self.show_available_commands,
            "hsr": self.hard_server_reset,
            "serversh": self.server_shutdown,
            "svicesh": self.server_service_shutdown,
            "sviceres": self.server_service_restart,
            "ls": self.list_connected_users,
            "quit": self.quit_command,
        }
    
    def show_available_commands(self, sock):
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
    
    def hard_server_reset(self, sock):
        try:
            sock.send((Colors.RED + "\nRESTARTING SERVER COMPUTER IN 10 SECONDS..." + Colors.RESET).encode())
        except:
            pass
        log("Server restart initiated by user.")
        time.sleep(10)
        os.system("reboot")
    
    def server_shutdown(self, sock):
        try:
            sock.send((Colors.RED + "\nSERVER SHUTTING DOWN IN 15 SECONDS..." + Colors.RESET).encode())
        except:
            pass
        log("Server shutdown initiated by user.")
        time.sleep(15)
        os.system("shutdown now")
    
    def server_service_shutdown(self, sock):
        try:
            sock.send((Colors.RED + "\nStopping server service in 5 seconds..." + Colors.RESET).encode())
        except:
            pass
        log("Server service shutdown initiated.")
        time.sleep(5)
        os._exit(1)
    
    def restart_server_service(self):
        log("Restarting server service...")
        os.execv(sys.executable, ['python'] + [sys.argv[0]])
    
    def server_service_restart(self, sock):
        try:
            sock.send((Colors.MAGENTA + "\nRestarting server service in 3 seconds..." + Colors.RESET).encode())
        except:
            pass
        
        # Broadcast without causing errors
        for client_sock in self.socket_list[:]:
            if client_sock != self.server_socket and client_sock != sock and client_sock.fileno() != -1:
                try:
                    client_sock.send((Colors.MAGENTA + "\nSERVER IS RESTARTING! Reconnect in a moment..." + Colors.RESET).encode())
                except:
                    pass
        
        time.sleep(3)
        threading.Thread(target=self.restart_server_service).start()
        os._exit(0)
    
    def quit_command(self, sock):
        username = self.user_manager.get_username(sock)
        try:
            sock.send((Colors.YELLOW + "Goodbye!\n" + Colors.RESET).encode())
        except:
            pass
        self.user_manager.disconnect_client(sock, self.socket_list)
    
    def unknown_command(self, sock):
        try:
            sock.send((Colors.RED + "Unknown command. Use $$[commands] for help.\n" + Colors.RESET).encode())
        except:
            pass
    
    def list_connected_users(self, sock):
        user_list = "\n--- Connected Users ---\n"
        for username in self.user_manager.users_sockets:
            user_list += f"- {username}\n"
        user_list += f"Total: {len(self.user_manager.users_sockets)}/{ROOM_CAPACITY}\n"
        user_list += "------------------------\n"
        try:
            sock.send((Colors.GREEN + user_list + Colors.RESET).encode())
        except:
            pass
    
    def process_command(self, command, sock):
        log_with_color("Command process initiated.", Colors.YELLOW)
        username = self.user_manager.get_username(sock)
        if not command:
            try:
                sock.send((Colors.RED + "Empty command.\n" + Colors.RESET).encode())
            except:
                pass
            return

        log(f"{username} issued command: $$[{command}]")
        
        handler = self.command_handlers.get(command, self.unknown_command)
        handler(sock)