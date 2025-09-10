import socket
import json
import sys
import logging # Added this import

# Configure client logging to a file for debugging
logging.basicConfig(
    filename='shell_client.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_command(operation, num1, num2, host='127.0.0.1', port=12345):
    """Sends a command to the persistent shell and returns the response."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.debug(f"Client attempting to connect to {host}:{port}")
        client_socket.connect((host, port))
        logging.debug(f"Client successfully connected to {host}:{port}")

        command = {
            "operation": operation,
            "num1": num1,
            "num2": num2
        }
        
        # Send the command as a JSON string
        logging.debug(f"Sending command: {json.dumps(command)}")
        client_socket.sendall(json.dumps(command).encode('utf-8'))
        logging.debug("Command sent. Awaiting response.")

        # Receive and decode the response
        response_raw = client_socket.recv(4096).decode('utf-8')
        logging.debug(f"Received raw response: {response_raw}")
        response_data = json.loads(response_raw)
        logging.debug(f"Decoded response: {response_data}")
        
        return response_data

    except ConnectionRefusedError:
        print(f"Error: Connection refused. Is the persistent shell running on {host}:{port}? "
              f"Please ensure you've run 'python launcher.py' first.", file=sys.stderr)
        return {"status": "error", "message": "Connection refused or server not running."}
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON response from server: {response_raw}", file=sys.stderr)
        return {"status": "error", "message": "Invalid JSON response from server."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}
    finally:
        client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python shell_client.py <operation> <num1> <num2>", file=sys.stderr)
        print("Example: python shell_client.py add 10 5", file=sys.stderr)
        sys.exit(1)

    operation = sys.argv[1].lower()
    try:
        num1 = float(sys.argv[2])
        num2 = float(sys.argv[3])
    except ValueError:
        print("Error: num1 and num2 must be numbers.", file=sys.stderr)
        sys.exit(1)

    # Validate operation
    if operation not in ['add', 'sub', 'mul']:
        print(f"Error: Unsupported operation '{operation}'. Supported operations are 'add', 'sub', 'mul'.", file=sys.stderr)
        sys.exit(1)

    print(f"Attempting to send command: {operation.upper()}({num1}, {num2})")
    result = send_command(operation, num1, num2)
    
    if result and result.get("status") == "success":
        print(f"Success! Result: {result.get('result')}")
    else:
        print(f"Failed! Details: {result.get('message', 'No message provided.')}")
