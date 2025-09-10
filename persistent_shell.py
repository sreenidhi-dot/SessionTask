import socket
import threading
import json
import logging
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import time

# Configure logging to a file when running as a service
# This is crucial because services don't have a console.
# Log file will be in the same directory as the script.
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persistent_shell_service.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG, # Changed to DEBUG for more verbose logging
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global variables for the server and event
server_socket = None
stop_event = None

def calculate_result(operation, num1, num2):
    """Performs the specified arithmetic operation."""
    if operation == 'add':
        return num1 + num2
    elif operation == 'sub':
        return num1 - num2
    elif operation == 'mul':
        return num1 * num2
    else:
        return None # Indicate unsupported operation

def handle_connection(client_sock):
    """Handles communication with a single client."""
    print(f"DEBUG: handle_connection thread started for {client_sock.getpeername()}") # Direct print for debug
    logging.debug(f"handle_connection thread started for {client_sock.getpeername()}") 
    try:
        print("DEBUG: Attempting to receive data...") # Direct print
        raw_request = client_sock.recv(4096).decode('utf-8')
        print(f"DEBUG: Received raw request: {raw_request}") # Direct print
        logging.info(f"Received: {raw_request}")
        
        try:
            data = json.loads(raw_request)
            print(f"DEBUG: Decoded data: {data}") # Direct print
            op = data.get('operation')
            n1 = data.get('num1')
            n2 = data.get('num2')

            if all(isinstance(arg, (int, float)) for arg in [n1, n2]) and op in ['add', 'sub', 'mul']:
                result = calculate_result(op, n1, n2)
                response_data = {"status": "success", "result": result}
                print(f"DEBUG: Calculated result: {result}") # Direct print
            else:
                response_data = {"status": "error", "message": "Invalid parameters or operation."}
            print(f"DEBUG: Response data before sending: {response_data}") # Direct print
        
        except Exception as e:
            response_data = {"status": "error", "message": f"Processing error: {type(e).__name__} - {e}"}
            print(f"DEBUG: Error during processing: {e}") # Direct print

        client_sock.sendall(json.dumps(response_data).encode('utf-8'))
        print("DEBUG: Response sent.") # Direct print

    except Exception as e:
        print(f"ERROR: Error handling client connection: {e}") # Direct print
        logging.error(f"Error handling client connection: {e}")
    finally:
        client_sock.close()
        print("DEBUG: Client connection closed.") # Direct print
        logging.info("Client connection closed.")

def run_server_logic(host='127.0.0.1', port=12345):
    """The actual server logic that runs in a thread."""
    global server_socket, stop_event
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
    except OSError as e:
        logging.error(f"Could not bind to port {port}: {e}. Service might not start.")
        servicemanager.LogMsg(servicemanager.EVENTLOG_ERROR_TYPE,
                              servicemanager.EvtMsgLogException,
                              (f"Service failed to bind to port {port}", ''))
        return # Exit if port is already in use or inaccessible
    logging.info(f"Persistent Shell Service before listening on {host}:{port}")    
    server_socket.listen(5)
    logging.info(f"Persistent Shell Service listening on {host}:{port}")

    while not stop_event.is_set(): # Use is_set() instead of deprecated isSet()
        try:
            server_socket.settimeout(1.0) # Allows server to check stop_event regularly
            client_socket, client_address = server_socket.accept()
            print(f"DEBUG: Accepted connection from {client_address[0]}:{client_address[1]}") # Direct print for debug
            logging.info(f"Accepted connection from {client_address[0]}:{client_address[1]}")
            logging.debug(f"Spawning thread for client {client_address[0]}:{client_address[1]}") # Added this log
            
            # Now, let's add a log before attempting to receive data
            logging.info(f"Attempting to receive data from {client_address[0]}:{client_address[1]}")

            thread = threading.Thread(target=handle_connection, args=(client_socket,))
            thread.daemon = True # Ensure client threads don't block service shutdown
            thread.start()
        except socket.timeout:
            continue # No connection in 1 sec, check stop_event again
        except Exception as e:
            logging.error(f"Error in server accept loop: {e}")
            break # Exit loop on unhandled error
    
    logging.info("Server socket closing.")
    if server_socket:
        server_socket.close()

class PersistentShellService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PersistentShellService"
    _svc_display_name_ = "Persistent Python Shell Service"
    _svc_description_ = "Provides add, subtract, and multiply functions via TCP socket in Session 0."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False
        self.server_thread = None
        global stop_event
        stop_event = win32event.CreateEvent(None, 0, 0, None) # Use win32event for service control

    def SvcStop(self):
        logging.info("PersistentShellService stopping.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        stop_event.set() # Signal the server thread to stop
        # Give a moment for the server loop to detect the stop event
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5) # Wait for thread to finish
        logging.info("PersistentShellService stopped.")
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        logging.getLogger().setLevel(logging.DEBUG) # Explicitly set logging level for the service process
        logging.info("PersistentShellService starting.")
        self.is_running = True
        
        # Determine port for service
        # If arguments are passed to the service, they would come via self._svc_args
        # For simplicity, we'll hardcode or make configurable via registry later.
        # For now, default to 12345 for Session 0 service.
        service_port = 12345 
        logging.info(f"Service will listen on port {service_port}")

        self.server_thread = threading.Thread(target=run_server_logic, args=('127.0.0.1', service_port))
        self.server_thread.daemon = False # Keep service thread alive
        self.server_thread.start()

        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        
        # Ensure server thread has indeed finished before reporting stopped
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=10) # Give it more time to close sockets etc.

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # This block is for running the server directly for debugging purposes.
        # It will not run as a Windows Service, but allows testing the server logic.
        print("Running server directly for debugging. Press Ctrl+C to stop.")
        try:
            # Configure logging for direct execution
            logging.basicConfig(
                filename=log_file_path,
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            stop_event = threading.Event() # Assign to the module-level global stop_event
            run_server_logic(port=12345) # Debug in current session
        except KeyboardInterrupt:
            stop_event.set()
            print("Server stopped by user.")
        except Exception as e:
            print(f"An error occurred during direct server run: {e}", file=sys.stderr)
    else:
        # This is the path for installing/managing the service
        win32serviceutil.HandleCommandLine(PersistentShellService)
