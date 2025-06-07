# server/logger.py
import time
from shared.config import Colors

def log(message):
    print(f"[SERVER LOG] {time.strftime('%H:%M:%S')} - {message}")

def log_with_color(message, color):
    print(f"{color}{message}{Colors.RESET}")