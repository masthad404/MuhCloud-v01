import sys
import socket
import select
import os
import time

def interface():
    os.system('clear')
    print(r"----------------------------------------------------------------------")
    print(r"\n\n")
    print(r"          _   _                             _ _         ")
    print(r"     /\  | | | |                           (_| |        ")
    print(r"    /  \ | |_| | ___  _ __ ___   ___  _ __  _| |_ _   _ ")
    print(r"   / /\ \| __| |/ _ \| '_ ` _ \ / _ \| '_ \| | __| | | |")
    print(r"  / ____ | |_| | (_) | | | | | | (_) | | | | | |_| |_| |")
    print(r" /_/    \_\\__|_|\___/|_| |_| |_|\___/|_| |_|_|\__|\__, |")
    print(r"                                                   __/ |")
    print(r"                                                  |___/ ")
    print(r"Local server communication with the base system by the Vogel projects")
    print("\n\n")
    print("---------------------------------------------------------------------")

def chat_client():
    if len(sys.argv) < 3:
        print('Usage: python client.py <hostname> <port>')
        sys.exit()

    host = sys.argv[1]
    port = int(sys.argv[2])
    connection_status = "disconnected"
    
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # CORRECTED: settimeout instead of setsockout
            connection_status = "connecting"
            sock.connect((host, port))
            sock.settimeout(None)
            connection_status = "connected"
            break
        except Exception as e:
            print(f"Connection failed: {e}")
            time.sleep(2)
            print("Retrying...")

    interface()
    print(f'Connected to {host}:{port}. Please login to continue.\n')
    print(f"Status: {connection_status.upper()}\n")

    try:
        while True:
            sockets_list = [sys.stdin, sock]
            read_sockets, _, _ = select.select(sockets_list, [], [], 1)

            for s in read_sockets:
                if s == sock:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            print("\nDisconnected from server.")
                            sock.close()
                            return
                        sys.stdout.write(data.decode('utf-8', errors="replace"))
                        sys.stdout.flush()
                    except:
                        print("\nConnection lost.")
                        sock.close()
                        return
                else:
                    msg = sys.stdin.readline().strip()
                    if msg:
                        if msg.lower() == "$$[quit]":
                            print("Disconnecting...")
                            sock.close()
                            return
                        try:
                            sock.send(msg.encode())
                        except:
                            print("\nFailed to send message.")
                            sock.close()
                            return
    except KeyboardInterrupt:
        print("\nDisconnecting gracefully...")
        try:
            sock.send(b"$$[quit]")
        except:
            pass
        try:
            sock.close()
        except:
            pass
        sys.exit(0)

if __name__ == "__main__":
    chat_client()