import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import sys
import socket
from server.server_core import chat_server, reset_server_state, set_shutdown_flag
from shared.config import Colors, PORT
from server.user_manager import UserManager

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Vogel Projects - Server Control Panel")
        self.root.geometry("1200x800")
        self.root.configure(bg="#0a192f")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.user_manager = UserManager()
        
        # Set dark theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background="#0a192f", foreground="#e6f1ff")
        self.style.configure('TFrame', background="#0a192f")
        self.style.configure('TLabel', background="#0a192f", foreground="#64ffda", font=('Roboto', 10))
        self.style.configure('TButton', background="#112240", foreground="#64ffda", 
                            font=('Roboto', 10), borderwidth=1)
        self.style.map('TButton', background=[('active', '#233554')])
        self.style.configure('Header.TLabel', font=('Roboto', 14, 'bold'), foreground="#64ffda")
        
        # Create main frames
        self.header_frame = ttk.Frame(root, padding=10)
        self.header_frame.pack(fill="x")
        
        self.status_frame = ttk.Frame(root, padding=10)
        self.status_frame.pack(fill="x")
        
        self.content_frame = ttk.Frame(root)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Header
        ttk.Label(self.header_frame, text="VOGEL PROJECTS SERVER", 
                 style="Header.TLabel").pack(side="left")
        ttk.Label(self.header_frame, text="Secure Messaging Platform", 
                 font=('Roboto', 12)).pack(side="left", padx=(10, 0))
        
        # Status indicators
        self.status_frame.columnconfigure(0, weight=1)
        self.status_frame.columnconfigure(1, weight=1)
        
        # Left status panel
        left_panel = ttk.Frame(self.status_frame)
        left_panel.grid(row=0, column=0, sticky="w")
        
        self.server_status = ttk.Label(left_panel, text="SERVER STATUS: OFFLINE")
        self.server_status.pack(anchor="w")
        
        self.active_users = ttk.Label(left_panel, text="ACTIVE USERS: 0")
        self.active_users.pack(anchor="w", pady=(5, 0))
        
        self.message_count = ttk.Label(left_panel, text="MESSAGES SENT: 0")
        self.message_count.pack(anchor="w", pady=(5, 0))
        
        # Right status panel
        right_panel = ttk.Frame(self.status_frame)
        right_panel.grid(row=0, column=1, sticky="e")
        
        ttk.Label(right_panel, text="CONNECTED USERS:").pack(anchor="e")
        self.user_list = tk.Listbox(right_panel, height=3, width=25, 
                                   bg="#112240", fg="#64ffda", 
                                   selectbackground="#233554", 
                                   font=('Roboto', 10), borderwidth=0)
        self.user_list.pack(anchor="e", pady=(5, 0))
        
        # Terminal output
        terminal_frame = ttk.Frame(self.content_frame)
        terminal_frame.pack(fill="both", expand=True)
        
        ttk.Label(terminal_frame, text="SERVER TERMINAL", 
                 style="Header.TLabel").pack(anchor="w", padx=5)
        
        self.terminal = scrolledtext.ScrolledText(
            terminal_frame, 
            bg="#0a192f", 
            fg="#e6f1ff", 
            insertbackground="white",
            font=('Consolas', 10),
            wrap="word",
            padx=10,
            pady=10
        )
        self.terminal.pack(fill="both", expand=True, padx=5, pady=5)
        self.terminal.configure(state="disabled")
        
        # Control buttons
        button_frame = ttk.Frame(root, padding=10)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Start Server", command=self.start_server)
        self.start_button.pack(side="left")
        
        self.stop_button = ttk.Button(button_frame, text="Stop Server", command=self.stop_server, state="disabled")
        self.stop_button.pack(side="left", padx=10)
        
        self.clear_button = ttk.Button(button_frame, text="Clear Terminal", command=self.clear_terminal)
        self.clear_button.pack(side="right")
        
        # Server variables
        self.server_thread = None
        self.running = False
        self.message_counter = 0
        self.last_update_time = 0
        self.start_time = 0
        
        # Redirect stdout to terminal
        self.original_stdout = sys.stdout
        sys.stdout = self
        
        # Start update loop
        self.update_ui()
    
    def write(self, message):
        """Redirect stdout to terminal widget"""
        self.terminal.configure(state="normal")
        self.terminal.insert("end", message)
        self.terminal.see("end")
        self.terminal.configure(state="disabled")
        
        # Also write to original stdout
        self.original_stdout.write(message)
        
        # Update message counter if it's a user message
        if " says: " in message:
            self.message_counter += 1
    
    def flush(self):
        """Flush method for stdout compatibility"""
        self.original_stdout.flush()
    
    def start_server(self):
        """Start the server in a separate thread"""
        if not self.running:
            self.running = True
            self.start_time = time.time()
            self.server_status.config(text="SERVER STATUS: ONLINE")
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.write("Starting server...\n")
            
            # Start server thread
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
    
    def run_server(self):
        """Wrapper to run the server with proper cleanup"""
        try:
            chat_server(self.user_manager)
        except Exception as e:
            self.write(f"Server crashed: {e}\n")
        finally:
            self.running = False
            self.server_status.config(text="SERVER STATUS: OFFLINE")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
    
    def stop_server(self):
        """Stop the server gracefully"""
        if self.running:
            self.write("Stopping server...\n")
            set_shutdown_flag(True)
            time.sleeo(0.5)
            reset_server_state(self.user_manager)
            
            # Give server time to shutdown
            time.sleep(0.5)
            
            # Reset state
            reset_server_state()
            
            self.running = False
            self.server_status.config(text="SERVER STATUS: OFFLINE")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
    
    def clear_terminal(self):
        """Clear the terminal output"""
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")
    
    def update_ui(self):
        """Update UI elements periodically"""
        if self.running:
            # Update user list
            self.user_list.delete(0, "end")
            for username in self.user_manager.users_sockets:
                self.user_list.insert("end", username)
            
            # Update status indicators
            self.active_users.config(text=f"ACTIVE USERS: {len(self.user_manager.users_sockets)}")
            self.message_count.config(text=f"MESSAGES SENT: {self.message_counter}")
            
            # Update timestamp every 5 seconds
            if time.time() - self.last_update_time > 5:
                self.last_update_time = time.time()
                uptime = time.time() - self.start_time
                hours, remainder = divmod(uptime, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.write(f"[SERVER] Uptime: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}\n")
        
        # Schedule next update
        self.root.after(1000, self.update_ui)
    
    def on_closing(self):
        """Handle window closing event"""
        self.stop_server()
        # Restore stdout
        sys.stdout = self.original_stdout
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()