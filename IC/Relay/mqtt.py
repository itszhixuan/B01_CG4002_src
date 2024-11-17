import paho.mqtt.client as mqtt
import json
from printer import log, THREAD


# MQTT parameters
# MQTT_BROKER = "p4361666.ala.asia-southeast1.emqxsl.com"
# MQTT_PORT = 8883

MQTT_BROKER = "" # TO FILL IN
MQTT_PORT = 1 # TO FILL IN
MQTT_USERNAME = "" # TO FILL IN
MQTT_PASSWORD = "" # TO FILL IN
MQTT_TOPIC = "" # TO FILL IN
SUB_TOPIC = "" # TO FILL IN


class MqttSubscriber:
    def __init__(self, message_queue):
        """
        Function to subscribe to the MQTT broker and receive messages.
        """
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_message = self.on_message

        # Set up TLS/SSL parameters
        # self.client.tls_set(
        #     cert_reqs=mqtt.ssl.CERT_NONE
        # )  # Disable certificate verification
        # self.client.tls_insecure_set(True)  # Allow insecure connection

        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.subscribe(SUB_TOPIC, qos=2)
        self.message_queue = message_queue

    def on_message(self, client, userdata, msg):
        """
        Callback function to handle received MQTT messages.
        """
        log(
            THREAD.RELAY_1,
            f"subscriber: received message: {msg.topic} -> {msg.payload.decode()}",
        )
        self.message_queue.put(msg.payload.decode())

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

        # Set up TLS/SSL parameters
        # self.client.tls_set(
        #     cert_reqs=mqtt.ssl.CERT_NONE
        # )  # Disable certificate verification
        # self.client.tls_insecure_set(True)  # Allow insecure connection

        # Connect to the MQTT broker
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.publish_queue = vis_message_queue

    def begin(self):
        # Start the loop in a separate thread
        self.client.loop_start()
        try:
            while True:
                # Wait for a message to be available in the queue
                message = self.publish_queue.get()
                if message is None:
                    break
                log(THREAD.PUB, f"publisher: Publishing message: {message}")
                parsed = json.loads(message)
                self.client.publish(parsed["topic"], parsed["payload"],qos=2)
        except Exception as e:
            print(e)
