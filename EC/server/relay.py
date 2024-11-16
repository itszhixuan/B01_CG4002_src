import mqtt
import threading
import queue
import json
import random

sub_queue = queue.Queue()
pub_queue = queue.Queue()


def generate_random_arrays():
    return [[random.randint(1, 10) for _ in range(10)] for _ in range(3)]


# Function to take keystrokes from user input
def capture_keystrokes():
    print("Start typing (press 'exit' to quit):")
    while True:
        keystroke = input()  # Capture user input
        if keystroke.lower() == "exit":  # Stop if 'exit' is typed
            break

        pub_queue.put(
            json.dumps(
                {
                    "topic": "default",
                    "payload": json.dumps(
                        {
                            "player_id": 1,
                            "action": "dummy",
                            "data": generate_random_arrays(),
                        }
                    ),
                }
            )
        )


def main():

    # Keep the main thread alive while the worker threads are running
    try:
        # Create and start the MQTT subscriber thread
        subscriber = mqtt.MqttSubscriber(sub_queue)
        subscriber_thread = threading.Thread(target=subscriber.begin, daemon=True)
        subscriber_thread.start()

        publisher = mqtt.MqttPublisher(pub_queue)
        publisher_thread = threading.Thread(target=publisher.begin, daemon=True)
        publisher_thread.start()

        # Set up threading for both producer and consumer
        producer_thread = threading.Thread(target=capture_keystrokes)

        # Start the threads
        producer_thread.start()

    except KeyboardInterrupt:
        print("Shutting down...")
        sub_queue.put(None)  # Stop signal for the message processor thread
        subscriber_thread.join()
        # Wait for producer thread to finish
        producer_thread.join()


if __name__ == "__main__":
    print("running main")
    main()
