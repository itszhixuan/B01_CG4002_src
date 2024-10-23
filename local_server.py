# server.py
import socket
import threading
from threading import Thread
import time
from examplemlscript import MLmodel  # Import the function from the other script

import ast

def send_data(connection, data):
    connection.sendall(str(data).encode())  # Send data to the client

def receive_data(connection) -> bytes:
        buffer = b""  # Holds the incoming data chunks
        data_length = None  # Length of the full data

        while True:
            chunk = connection.recv(2048)
            if not chunk:
                # If recv returns an empty byte string, the connection is closed
                raise ConnectionError("Socket connection closed prematurely")

            buffer += chunk

            # If data length is not determined, check if we have received the full length prefix
            if data_length is None:
                if b"_" in buffer:
                    # split at first occurrence of _ to get the length of the payload
                    length_str, remaining = buffer.split(b"_", 1)
                    try:
                        data_length = int(length_str.decode("utf-8"))
                    except ValueError:
                        raise ValueError("Invalid length prefix received")

                    # The remaining part of the buffer is part of the actual data
                    buffer = remaining

            # If the total data received matches or exceeds the expected length, we are done
            if data_length is not None and len(buffer) >= data_length:
                # Extract the full data portion
                full_data = buffer[:data_length]
                return full_data
        
# Thread 3: Reads from the receive_queue, processes the data, and puts it in the send_queue
def process_data(conn):
    print("process_data starting")
    while True:

        print("receiving data")
        data_string = receive_data(conn).decode()

        print(f"Complete Data for ML: {data_string}")
        if data_string:
            data = ast.literal_eval(data_string)
            processed_data = MLmodel(data)

            print(f"Processed data: {processed_data}")
            send_data(conn,processed_data)

def start_server():
    #host = "localhost"
    host = "0.0.0.0"
#     host = "127.0.0.1"
    port = 65433
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print("Server: Listening for connections...")
        
        while True:
            try:
                conn, addr = s.accept()
                print(f"Server: Connected to {addr}")
                process_data(conn)
            except Exception as e:
                conn.close()
                print(f"exception: {e}")

if __name__ == "__main__":
    start_server()  