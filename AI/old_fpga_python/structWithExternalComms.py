import queue
import threading
import time
import os
from examplemlscript import MLmodel  # Import the function from the other script
import asyncio

# Create two OS pipes: one for input and one for output
pipe_in_read, pipe_in_write = os.pipe()  # For receiving data from the OS pipe
pipe_out_read, pipe_out_write = os.pipe()  # For writing data into the OS pipe

# Message queues for communication between threads
receive_queue = queue.Queue()  # Queue to store received data
send_queue = queue.Queue()  # Queue to store data to be sent


# Thread 1: Reads data from the OS pipe and puts it into the message queue
def read_from_pipe(pipe_read, msg_queue):
    while True:
        try:
            # Read data from the pipe (1024 bytes at a time)
            data = os.read(pipe_read, 2048).decode()
            if data:
                print(f"Received from pipe: {data}")
                # Put data into the message queue
                msg_queue.put(data)
            time.sleep(1)
        except Exception as e:
            print(f"Error reading from pipe: {e}")
            break


# Thread 2: Reads data from the message queue and writes it to the OS pipe
def write_to_pipe(pipe_write, msg_queue):
    while True:
        try:
            # Wait until there is data to send
            data = msg_queue.get()
            if data:
                print(f"Sending to pipe: {data}")
                # Write data to the pipe
                os.write(pipe_write, data.encode())
            time.sleep(1)
        except Exception as e:
            print(f"Error writing to pipe: {e}")
            break


# Start the thread that reads from the pipe and sends to the message queue
receive_thread = threading.Thread(
    target=read_from_pipe, args=(pipe_in_read, receive_queue)
)
receive_thread.daemon = True
receive_thread.start()

# Start the thread that reads from the message queue and writes to the pipe
send_thread = threading.Thread(target=write_to_pipe, args=(pipe_out_write, send_queue))
send_thread.daemon = True
send_thread.start()


# Simulating data writing to the 'send_queue' to be sent through the output pipe
def simulate_data_input():
    while True:
        data = input("Enter data to send: ")
        os.write(pipe_in_write, data.encode())


simulate_input_thread = threading.Thread(target=simulate_data_input)
simulate_input_thread.daemon = True
simulate_input_thread.start()


# Read from the 'pipe_out_read' to simulate a separate process that gets the output
def simulate_pipe_output():
    while True:
        try:
            data = os.read(pipe_out_read, 1024).decode()
            if data:
                print(f"Simulated external process received: {data}")
        except Exception as e:
            print(f"Error reading from output pipe: {e}")
            break


simulate_output_thread = threading.Thread(target=simulate_pipe_output)
simulate_output_thread.daemon = True
simulate_output_thread.start()


# Thread 3: Reads from the receive_queue, processes the data, and puts it in the send_queue
def process_data(receive_queue, send_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
#         try:
            # Get data from the receive_queue
            data = receive_queue.get()
            print(data)
            if data:
                # Process the data (Put your processing logic here)
                processed_data = MLmodel(data)
                # processed_data = data

                print(f"Processed data: {processed_data}")

                # Put the processed data in the send_queue
                send_queue.put(processed_data)
            time.sleep(1)
#         except Exception as e:
#             print(f"Error processing data: {e}")
#             break


# Start the thread that processes data from the receive queue and passes it to the send queue
process_thread = threading.Thread(target=process_data, args=(receive_queue, send_queue))
process_thread.daemon = True
process_thread.start()

# Keep the main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Terminating...")
