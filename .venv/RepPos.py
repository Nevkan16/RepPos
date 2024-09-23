import tkinter as tk
from tkinter import scrolledtext
import ctypes
import time
import threading
import json
import os
import configparser

# File to save the window position of "Replayer"
window_position_file = 'rep_position.json'

# File to save the position of the main application window
CONFIG_FILE = 'win_position.ini'

# Global variables
hwnd = None
MAX_LOG_ROWS = 4

# Window title to look for
window_title = "Replayer"

# Load user32.dll
user32 = ctypes.WinDLL('user32', use_last_error=True)

# Functions from user32.dll
FindWindow = user32.FindWindowW
IsWindow = user32.IsWindow
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect
SetWindowPos = user32.SetWindowPos

# Constants for window positioning
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

# Define RECT structure
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]

def get_window_position(hwnd):
    """Получение текущей позиции и размеров окна"""
    if hwnd and IsWindow(hwnd):
        rect = RECT()
        GetWindowRect(hwnd, ctypes.byref(rect))
        position = {
            'x': rect.left,
            'y': rect.top,
            'width': rect.right - rect.left,
            'height': rect.bottom - rect.top
        }
        return position
    else:
        return None

def save_window_position_to_file(position):
    """Сохранение позиции окна в файл .json"""
    if position:
        with open(window_position_file, 'w') as file:
            json.dump(position, file)
        add_log(f"Window position saved to file: {position}")

def load_window_position_from_file():
    """Загрузка сохранённой позиции окна из файла .json"""
    if os.path.exists(window_position_file):
        with open(window_position_file, 'r') as file:
            position = json.load(file)
            return position
    else:
        return None

def set_window_position(hwnd, position):
    """Установка позиции окна"""
    if hwnd and IsWindow(hwnd) and position:
        SetWindowPos(
            hwnd,
            None,
            position['x'],
            position['y'],
            position['width'],
            position['height'],
            SWP_NOZORDER | SWP_NOACTIVATE
        )

def find_window_by_title(title):
    """Поиск окна по заголовку"""
    hwnd = FindWindow(None, title)
    if hwnd and IsWindowVisible(hwnd):
        return hwnd
    else:
        return None

def monitor_window_position(log_text, exit_event):
    """Мониторинг окна и сохранение позиции при его закрытии, с постоянным отображением координат"""
    global hwnd
    window_found = False
    last_position = None

    while not exit_event.is_set():
        hwnd = find_window_by_title(window_title)

        if hwnd is None:
            if window_found:
                add_log(f"Window '{window_title}' has been closed or is not visible.")
                window_found = False

                # Save the current position to the file only when the window closes
                if last_position:
                    save_window_position_to_file(last_position)

            time.sleep(2)
            continue

        if not window_found:
            add_log(f"Window '{window_title}' found and is visible.")
            window_found = True

            # Load and apply the saved position if available
            saved_position = load_window_position_from_file()
            if saved_position:
                set_window_position(hwnd, saved_position)

        # Continuously track the current window position
        current_position = get_window_position(hwnd)
        if current_position:
            last_position = current_position  # Keep track of the last known position
            add_log(f"x: {current_position['x']},\ny: {current_position['y']},\n"
                    f"width: {current_position['width']},\nheight: {current_position['height']}")

        time.sleep(2)

def save_win_position(root):
    """Save the current position of the window to a config file."""
    config = configparser.ConfigParser()
    config['WindowPosition'] = {
        'x': root.winfo_x(),
        'y': root.winfo_y()
    }
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def load_win_position():
    """Load the window position from the config file."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if 'WindowPosition' in config:
        x = config.getint('WindowPosition', 'x', fallback=100)
        y = config.getint('WindowPosition', 'y', fallback=100)
        return x, y
    return 100, 100

def add_log(message):
    log_text.config(state=tk.NORMAL)
    log_text.delete(1.0, tk.END)  # Clear the log
    formatted_message = message.replace(", ", ",")
    log_text.insert(tk.END, formatted_message)
    log_text.config(state=tk.DISABLED)
    log_text.yview(tk.END)

def copy_selection(event=None):
    root.clipboard_clear()
    text = log_text.selection_get()
    root.clipboard_append(text)

def show_context_menu(event):
    context_menu.post(event.x_root, event.y_root)

def main():
    global root, log_text, context_menu, exit_event

    root = tk.Tk()
    root.title("Replayer Position")

    # Load window position for the main application window
    x, y = load_win_position()
    root.geometry(f"280x120+{x}+{y}")
    root.resizable(False, False)

    log_text = scrolledtext.ScrolledText(root, height=MAX_LOG_ROWS, width=50)
    log_text.pack()

    # Context menu for copying text
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Copy", command=copy_selection)

    log_text.bind("<Button-3>", show_context_menu)  # Right-click to show context menu
    log_text.bind("<Control-c>", copy_selection)  # Ctrl+C to copy selected text

    exit_event = threading.Event()  # Event to stop the monitoring thread
    monitor_thread = None

    def start_monitor():
        nonlocal monitor_thread
        exit_event.clear()
        start_button.config(state="disabled")
        finish_button.config(state="normal")
        monitor_thread = threading.Thread(target=monitor_window_position, args=(log_text, exit_event))
        monitor_thread.daemon = True
        monitor_thread.start()
        add_log("Monitoring started.")

    def finish_monitor():
        nonlocal monitor_thread
        exit_event.set()
        if monitor_thread is not None:
            monitor_thread.join()
        start_button.config(state="normal")
        finish_button.config(state="disabled")
        add_log("Monitoring stopped.")

    def on_closing():
        finish_monitor()
        save_win_position(root)  # Save the window position when closing
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    start_button = tk.Button(root, text="Start", command=start_monitor)
    start_button.pack(side=tk.LEFT, padx=5, pady=5)

    finish_button = tk.Button(root, text="Finish", command=finish_monitor, state="disabled")
    finish_button.pack(side=tk.LEFT, padx=5, pady=5)

    # Automatically start the monitor
    start_monitor()

    root.mainloop()

if __name__ == "__main__":
    main()
