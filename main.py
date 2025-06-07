# main.py
from server.server_gui import ServerGUI
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()