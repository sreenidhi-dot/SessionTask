import socket
import json
import sys
import time

def test_connection(host='127.0.0.1', port=12348):
    """Test connection to the service with detailed debugging."""
    print(f"Testing connection to {host}:{port}")
    
    try:
        # Create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Socket created successfully")
        
        # Set timeout to avoid hanging
        client_socket.settimeout(10.0)  # 10 second timeout
        print("Timeout set to 10 seconds")
        
        # Connect
        print("Attempting to connect...")
        client_socket.connect((host, port))
        print("✓ Connected successfully!")
        
        # Prepare command
        command = {
            "operation": "add",
            "num1": 5.0,
            "num2": 3.0
        }
        
        # Send command
        print(f"Sending command: {command}")
        command_json = json.dumps(command)
        client_socket.sendall(command_json.encode('utf-8'))
        print("Command sent successfully!")
        
        # Try to receive response
        print("Waiting for response...")
        try:
            response_raw = client_socket.recv(4096)
            print(f"Received {len(response_raw)} bytes")
            
            if response_raw:
                response_str = response_raw.decode('utf-8')
                print(f"Raw response: {response_str}")
                
                try:
                    response_data = json.loads(response_str)
                    print(f"Parsed response: {response_data}")
                    
                    if response_data.get("status") == "success":
                        print(f"SUCCESS! Result: {response_data.get('result')}")
                    else:
                        print(f"Server returned error: {response_data.get('message')}")
                        
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON response: {e}")
                    print(f"Raw response was: {repr(response_str)}")
            else:
                print("Received empty response")
                
        except socket.timeout:
            print("TIMEOUT: No response received within 10 seconds")
            print("This suggests the server accepted the connection but didn't send a response")
            
        except Exception as e:
            print(f"Error receiving response: {e}")
            
    except ConnectionRefusedError:
        print("CONNECTION REFUSED: Service is not listening on this port")
        
    except socket.timeout:
        print("CONNECTION TIMEOUT: Could not connect within 10 seconds")
        
    except Exception as e:
        print(f"Connection error: {e}")
        
    finally:
        try:
            client_socket.close()
            print("Socket closed")
        except:
            pass

def check_service_status():
    """Check if the service is running."""
    import subprocess
    try:
        result = subprocess.run(['sc', 'query', 'FixedMinimalService'], 
                              capture_output=True, text=True)
        if 'RUNNING' in result.stdout:
            print("FixedMinimalService is RUNNING")
            return True
        else:
            print("FixedMinimalService is NOT running")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"Could not check service status: {e}")
        return False

if __name__ == "__main__":
    print("=== Session 0 Service Debug Test ===")
    print()
    
    # Check service status first
    print("1. Checking service status...")
    if not check_service_status():
        print("Please start the MinimalTestService first")
        sys.exit(1)
    
    print()
    print("2. Testing connection...")
    test_connection()
    
    print()
    print("=== Test Complete ===")
