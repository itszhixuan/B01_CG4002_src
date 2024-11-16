import queue
import threading
import time

pipe_in_read = "/home/xilinx/ai_in_eval_out"
pipe_out_write = "/home/xilinx/ai_out_eval_in"


# Thread 1: Reads data from the OS pipe and puts it into the message queue
def read_from_pipe(pipe_read, msg_queue):
    with open(pipe_read, "r") as pipe:
        while True:
            try:
                # Read data from the pipe (1024 bytes at a time)
                # data = os.read(pipe_read, 2048).decode()
                data = pipe.read()
                if data:
                    print(f"Received from pipe: {data}")
                    # Put data into the message queue
                    msg_queue.put(data)
            except Exception as e:
                print(f"Error reading from pipe: {e}")
                break


# Thread 2: Reads data from the message queue and writes it to the OS pipe
def write_to_pipe(pipe_write, msg_queue):
    with open(pipe_write, "w") as pipe:
        while True:
            try:
                # Wait until there is data to send
                data = msg_queue.get()
                if data:
                    print(f"Sending to pipe: {data}")
                    # Write data to the pipe
                    # os.write(pipe_write, str(data).encode())
                    datastring = str(data)
                    pipe.write(
                        datastring + "\n"
                    )  # Adding a newline to ensure it's properly written
                    pipe.flush()
            except Exception as e:
                print(f"Error writing to pipe: {e}")
                break


# returns queues for talking to ai
def init_ai_comms():
    # Message queues for communication between threads
    receive_queue = queue.Queue()  # Queue to store received data
    send_queue = queue.Queue()  # Queue to store data to be sent

    # Start the thread that reads from the pipe and sends to the message queue
    receive_thread = threading.Thread(
        target=read_from_pipe, args=(pipe_in_read, receive_queue)
    )
    receive_thread.daemon = True
    receive_thread.start()

    # Start the thread that reads from the message queue and writes to the pipe
    send_thread = threading.Thread(
        target=write_to_pipe, args=(pipe_out_write, send_queue)
    )
    send_thread.daemon = True
    send_thread.start()

    return receive_queue, send_queue
