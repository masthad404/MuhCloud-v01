# server/user_manager.py
import socket
import time
from server.logger import log, log_with_color
from shared.config import Colors, RECV_BUFFER, USERS, HOST, PORT, ROOM_CAPACITY

class UserManager:
    def __init__(self):
        self.users_sockets = {}
        self.active_connections = {}
    
    def get_username(self, sock):
        for username, user_sock in self.users_sockets.items():
            if user_sock == sock:
                return username
        return "Unknown"
    
    def authenticate(self, sock):
        log_with_color("Authentication process initiated.", Colors.YELLOW)
        
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
            return None, None

        if username in USERS and USERS[username] == password:
            old_sock = None
            if username in self.users_sockets:
                old_sock = self.users_sockets[username]
                log(f"Duplicate login detected for {username}")
            
            self.active_connections[username] = time.time()
            self.users_sockets[username] = sock
            
            log(f"{username} authenticated successfully")
            
            welcome_msg = Colors.GREEN + f"\nAuthentication successful! Connected to server.\n"
            welcome_msg += f"Server info: {HOST}:{PORT}\n"
            welcome_msg += f"Room capacity: {ROOM_CAPACITY} users\n"
            welcome_msg += f"Active users: {len(self.users_sockets)}\n" + Colors.RESET
            try:
                sock.send(welcome_msg.encode())
            except:
                pass
            
            return username, old_sock

        else:
            try:
                sock.send("Authentication failed. Disconnecting...\n".encode())
            except:
                pass
            try:
                sock.close()
            except:
                pass
            return None, None
    
    def disconnect_client(self, sock):
        log_with_color("Disconnect client initiated", Colors.YELLOW)
        username = self.get_username(sock)
        if username != "Unknown":
            if username in self.users_sockets and self.users_sockets[username] == sock:
                del self.users_sockets[username]
                log(f"Removed {username} from users_sockets")
            
            if username in self.active_connections:
                del self.active_connections[username]
        
        log(f"{username} disconnected cleanly")
        return username