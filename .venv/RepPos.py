import tkinter as tk
from tkinter import scrolledtext
import ctypes
import time
import threading

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
GetWindowRect = user32.GetWindowRect  # Добавляем GetWindowRect для получения позиции окна

# Define RECT structure
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]

def get_window_position(hwnd):
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
        add_log("Invalid window handle. Cannot get window position.")
        return None

def find_window_by_title(title):
    hwnd = FindWindow(None, title)
    if hwnd and IsWindowVisible(hwnd):  # Проверяем видимость окна
        return hwnd
    else:
        return None  # Возвращаем None, если окно не найдено или невидимо

def monitor_window_position(log_text, exit_event):
    global hwnd
    window_found = False  # Flag to track if the window has been found

    while not exit_event.is_set():
        hwnd = find_window_by_title(window_title)

        if hwnd is None:
            if window_found:
                add_log(f"Window '{window_title}' has been closed or is not visible.")
                window_found = False
            time.sleep(2)
            continue

        if not window_found:
            add_log(f"Window '{window_title}' found and is visible.")
            window_found = True

        if hwnd and IsWindow(hwnd):
            current_position = get_window_position(hwnd)
            if current_position:
                add_log(f"x - {current_position['x']},\n"
                        f"y - {current_position['y']}.\n"
                        f"w - {current_position['width']},\n"
                        f"h - {current_position['height']}.")

        time.sleep(2)

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
    root.title("Window Position")
    root.geometry("280x120")
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
