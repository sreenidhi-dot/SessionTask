import subprocess
import sys
import time
import threading

def start_persistent_shell():
    # Command to run the persistent_shell.py script on port 12345
    command = [sys.executable, 'persistent_shell.py', '12345']

    try:
        # Launch the persistent shell as a detached process
        process = subprocess.Popen(command,
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        
        pid = process.pid
        print(f"Persistent shell (Session 1) started with PID: {pid}")
        
        time.sleep(2) # Give the server a moment to start up
        
        # Start a background thread to read and display logs from the shell's stderr
        def log_reader(process_obj):
            for line in process_obj.stderr:
                print(f"SHELL LOG (PID {pid}): {line.decode().strip()}")

        log_thread = threading.Thread(target=log_reader, args=(process,))
        log_thread.daemon = True # Ensure thread exits with main program
        log_thread.start()

    except FileNotFoundError:
        print(f"ERROR: Python executable not found at {sys.executable}. Ensure Python is in PATH.", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Failed to launch persistent shell: {e}", file=sys.stderr)

if __name__ == "__main__":
    start_persistent_shell()
