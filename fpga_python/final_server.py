# server.py
import socket
import threading
from threading import Thread
import time
from pynq import Overlay, allocate
import pynq.lib.dma
import sys, os
import numpy as np
import struct
import sys
import ast
import time
import signal

N_SAMPLES = 80
N_FEATURES = 6
N_WINDOWS = 38

overlay = None
dma_send = None
dma_recv = None
input_buffer = None
output_buffer = None

def initialise():
    
    global overlay, dma_send, dma_recv, input_buffer, output_buffer
    
    curr_dir = sys.path[0]
    overlay = Overlay(os.path.join(curr_dir, 'final.bit'))

    dma = overlay.dma
    dma_send = dma.sendchannel
    dma_recv = dma.recvchannel

    input_buffer = allocate(shape=(456,), dtype=np.int32)
    output_buffer = allocate(shape=(1,), dtype=np.int32)
    
    print("Overlay setup done")

def preprocess(raw_data):
    # [[[12776, -3608, -12876, -261, -57, 669], ... (80x6x2) 
    def smoothen_imu_data(data, window_size=5, stride=2):
        # [[12776, -3608, -12876, -261, -57, 669], ... (80x6)

        data = np.array(data)
        shape = (N_WINDOWS, window_size, N_FEATURES)
        strides = (data.strides[0] * stride, *data.strides)
        sliding_windows = np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)

        smoothened_imu = sliding_windows.mean(axis=1)
        # Output: (38x6)
        return smoothened_imu

    hand_df = smoothen_imu_data(raw_data[0])
    leg_df = smoothen_imu_data(raw_data[1])

    flattened = np.concatenate((hand_df.flatten(), leg_df.flatten()))
    return flattened.tolist()

def float_to_int_array(floats):
    return np.frombuffer(np.array(floats, dtype=np.float32).tobytes(), dtype=np.int32)

def temperature_scaled_probability(logits, temperature):
    # Convert logits to numpy array if they're not already
    logits = np.array(logits)
    
    # Scale the logits by dividing by the temperature
    scaled_logits = logits / temperature
    
    # Apply softmax to get the probabilities
    exp_logits = np.exp(scaled_logits - np.max(scaled_logits))  # Subtract max for numerical stability
    probabilities = exp_logits / exp_logits.sum()
    
    # Get the probability of the predicted (highest logit) value
    predicted_index = np.argmax(logits)  # Find the index of the max logit in original logits
    predicted_probability = probabilities[predicted_index]
    
    return predicted_probability

def generate_output(output_array):
    return output_array.index(max(output_array))

def MLmodel(raw_data):
    start_time = time.time()
    processed_data = preprocess(raw_data)
    end_time = time.time()
    print('sliding window time taken:', end_time - start_time)
    
    start_time = time.time()
    int_data = float_to_int_array(processed_data)
    end_time = time.time()
    print('float to int time taken:', end_time - start_time)
    
    input_buffer[:] = int_data
    
    output_buffer.fill(0)
    dma_send.transfer(input_buffer)
    dma_recv.transfer(output_buffer)
    dma_send.wait()
    dma_recv.wait()
    
    prediction = output_buffer.copy()
    print(prediction)
    
    values = []
    start_time = time.time()
    for i in range(10):
        output_buffer.fill(0)
        dma_recv.transfer(output_buffer)
        dma_recv.wait()
        values[i] = output_buffer[0]
#         print(output_buffer)
        dma_recv.transfer(output_buffer)
        dma_recv.wait()
#         print("positive")
#         print(output_buffer)
        if (output_buffer[0] != 0):
            values[i] += (256 * output_buffer[0])
        dma_recv.transfer(output_buffer)
        dma_recv.wait()
#         print("negative")
#         print(output_buffer)
        if (output_buffer[0] != 0):
            values[i] += (-256 * output_buffer[0])
    end_time = time.time()
    print('extract logits time taken:', end_time - start_time)
#     print(values)

    T = 1
    predicted_prob = temperature_scaled_probability(values, T)

    print(predicted_prob)
    
    if predicted_prob < 0.94:
        prediction = [9]
    return prediction
    
    
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

        #print(f"Complete Data for ML: {data_string}")
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

def main():
    initialise()
    start_server()
    
def handle_sigint(signum, frame):
    print("Shutting down server")
    sys.exit(0)
    
signal.signal(signal.SIGINT, handle_sigint)
        
if __name__ == "__main__":
    main()  