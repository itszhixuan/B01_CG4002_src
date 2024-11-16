import paho.mqtt.client as mqtt
import json
from printer import log, THREAD

DEBUG_LOGGING = False

# MQTT parameters
MQTT_BROKER = "188.166.189.38"
# MQTT_BROKER = "p4361666.ala.asia-southeast1.emqxsl.com"
MQTT_PORT = 1883
# MQTT_PORT = 8883
MQTT_USERNAME = "user"
MQTT_PASSWORD = "capstone"  # not good practice to commit passwords but whatever
MQTT_TOPIC = "default"


class MqttSubscriber:
    def __init__(self, message_queue):
        """
        Function to subscribe to the MQTT broker and receive messages.
        """
        self.client = mqtt.Client(clean_session=True)
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_message = self.on_message

        # Set up TLS/SSL parameters
        # self.client.tls_set(
        #     cert_reqs=mqtt.ssl.CERT_NONE
        # )  # Disable certificate verification
        # self.client.tls_insecure_set(True)  # Allow insecure connection

        # # set up handler for disconnect
        # self.client.on_connect = self.on_connect
        # self.client.on_disconnect = self.on_disconnect

        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.subscribe(MQTT_TOPIC)
        self.message_queue = message_queue

    # Define the callback for connection
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log(THREAD.RELAY_1, "Connected to broker")
        else:
            log(THREAD.RELAY_1, f"Failed to connect, return code {rc}")

    # Define the callback for disconnect
    def on_disconnect(self, client, userdata, rc):
        log(THREAD.RELAY_1, f"Disconnected from broker, return code {rc}")
        # Optionally, you can try to reconnect here or let the client reconnect automatically
        if rc != 0:
            print("Attempting to reconnect...")
            log(THREAD.RELAY_1, f"Attempting to reconnect...")
            client.reconnect()  # Handle reconnect if auto-reconnect isn't enabled

    def on_message(self, client, userdata, msg):
        """
        Callback function to handle received MQTT messages.
        """
        self.message_queue.put(msg.payload.decode())
        if DEBUG_LOGGING:
            log(
                THREAD.RELAY_1,
                f"subscriber: received message: {msg.topic} -> {msg.payload.decode()}",
            )
        else:
            log(
                THREAD.RELAY_1,
                f"subscriber: received message: {msg.topic}",
            )

    def begin(self):
        """
        begin loop
        """
        log(THREAD.RELAY_1, "subscriber: beginning mqtt")
        self.client.loop_forever()


class MqttPublisher:
    def __init__(self, vis_message_queue):
        # Create an MQTT client instance
        self.client = mqtt.Client()

        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        # self.client.on_publish = self.on_publish

        # Set up TLS/SSL parameters
        # self.client.tls_set(
        #     cert_reqs=mqtt.ssl.CERT_NONE
        # )  # Disable certificate verification
        # self.client.tls_insecure_set(True)  # Allow insecure connection

        ## set up handler for disconnect
        ## disabling these seems to make publishing more consistent
        # self.client.on_connect = self.on_connect
        # self.client.on_disconnect = self.on_disconnect

        # Connect to the MQTT broker
        err = self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        if err != 0:
            log(THREAD.PUB, f"publisher: error connecting to mqtt {err}")
            raise Exception(f"publisher: error connecting to mqtt {err}")
        self.publish_queue = vis_message_queue

    # Define the callback for connection
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log(THREAD.PUB, "Connected to broker")
        else:
            log(THREAD.PUB, f"Failed to connect, return code {rc}")

    # Define the callback for disconnect
    def on_disconnect(self, client, userdata, rc):
        log(THREAD.PUB, f"Disconnected from broker, return code {rc}")
        # Optionally, you can try to reconnect here or let the client reconnect automatically
        if rc != 0:
            print("Attempting to reconnect...")
            log(THREAD.PUB, f"Attempting to reconnect...")
            client.reconnect()  # Handle reconnect if auto-reconnect isn't enabled

    def on_publish(self, client, userdata, mid):
        print("publish success")

    def begin(self):
        # Start the loop in a separate thread
        log(THREAD.PUB, "publisher: beginning mqtt")
        try:
            self.client.loop_start()
            while True:
                # Wait for a message to be available in the queue
                message = self.publish_queue.get()
                if message is None:
                    break

                if DEBUG_LOGGING:
                    log(THREAD.PUB, f"publisher: Publishing message {message}")
                else:
                    log(THREAD.PUB, "publisher: Publishing message")
                parsed = json.loads(message)
                self.client.publish(
                    parsed["topic"], parsed["payload"], qos=2, retain=False
                )
        except Exception as e:
            print(e)
