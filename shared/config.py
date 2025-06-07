# shared/config.py

class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"

# Server configuration
HOST = ''
PORT = 9009
RECV_BUFFER = 4096
ROOM_CAPACITY = 3

# User credentials
USERS = {
    "user1": "1234",
    "user2": "1234",
    "user3": "1234"
}