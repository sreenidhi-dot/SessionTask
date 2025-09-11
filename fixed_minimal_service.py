import socket
import threading
import json
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import tempfile

# Global variables
server_socket = None
stop_event = None

# Use project directory for logs as requested
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'minimal_service.log')

def log_message(message):
    """Write log message to both file and Windows Event Log."""
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"{message}\n")
    except:
        pass  # If file logging fails, continue
    
    try:
        servicemanager.LogInfoMsg(f"MinimalTestService: {message}")
    except:
        pass  # If event log fails, continue

def simple_handle_connection(client_sock):
    """Minimal connection handler for Session 0 testing."""
    try:
        log_message(f"Connection accepted from {client_sock.getpeername()}")
        
        # Receive data
        raw_request = client_sock.recv(4096).decode('utf-8')
        log_message(f"Received: {raw_request}")
        
        # Parse JSON
        data = json.loads(raw_request)
        operation = data.get('operation')
        num1 = data.get('num1', 0)
        num2 = data.get('num2', 0)
        
        # Simple calculation
        if operation == 'add':
            result = num1 + num2
        elif operation == 'sub':
            result = num1 - num2
        elif operation == 'mul':
            result = num1 * num2
        else:
            result = 0
        
        # Send response
        response = {"status": "success", "result": result}
        response_json = json.dumps(response)
        client_sock.sendall(response_json.encode('utf-8'))
        
        log_message(f"Sent response: {response_json}")
        
    except Exception as e:
        log_message(f"Error in handle_connection: {str(e)}")
        error_response = {"status": "error", "message": str(e)}
        try:
            client_sock.sendall(json.dumps(error_response).encode('utf-8'))
        except:
            pass
    finally:
        try:
            client_sock.close()
            log_message("Connection closed")
        except:
            pass

def run_minimal_server(host='127.0.0.1', port=12348):  # New port
    """Minimal server for Session 0 testing."""
    global server_socket, stop_event
    
    log_message("Starting run_minimal_server function")
    
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        log_message("Socket created and configured")
        
        server_socket.bind((host, port))
        log_message(f"Socket bound to {host}:{port}")
        
        server_socket.listen(5)
        log_message(f"Socket listening on {host}:{port}")
        
        # Handle different event types (win32event vs threading.Event)
        while True:
            # Check if we should stop (works for both event types)
            if hasattr(stop_event, 'is_set'):
                # This is a threading.Event (direct execution)
                if stop_event.is_set():
                    break
            else:
                # This is a win32event (service execution)
                if win32event.WaitForSingleObject(stop_event, 0) == win32event.WAIT_OBJECT_0:
                    break
            
            try:
                server_socket.settimeout(1.0)
                client_socket, client_address = server_socket.accept()
                log_message(f"Accepted connection from {client_address}")
                
                # Handle in new thread
                thread = threading.Thread(target=simple_handle_connection, args=(client_socket,))
                thread.daemon = True
                thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                log_message(f"Server error: {str(e)}")
                break
    
    except Exception as e:
        log_message(f"Bind/Listen error: {str(e)}")
    finally:
        if server_socket:
            server_socket.close()
            log_message("Server socket closed")

class FixedMinimalService(win32serviceutil.ServiceFramework):
    _svc_name_ = "FixedMinimalService"
    _svc_display_name_ = "Fixed Minimal Session 0 Test Service"
    _svc_description_ = "Fixed test service for Session 0 communication"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.server_thread = None
        global stop_event
        stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        log_message("Service stopping...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        stop_event.set()
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
        
        log_message("Service stopped")
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        log_message("Service starting in SvcDoRun...")
        
        try:
            self.server_thread = threading.Thread(target=run_minimal_server, args=('127.0.0.1', 12348))
            self.server_thread.daemon = False
            self.server_thread.start()
            log_message("Server thread started")

            # Wait for stop signal
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=10)
                
        except Exception as e:
            log_message(f"Error in SvcDoRun: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Running fixed server directly for debugging. Press Ctrl+C to stop.")
        try:
            stop_event = threading.Event()
            run_minimal_server(port=12348)
        except KeyboardInterrupt:
            stop_event.set()
            print("Server stopped by user.")
    else:
        win32serviceutil.HandleCommandLine(FixedMinimalService)
