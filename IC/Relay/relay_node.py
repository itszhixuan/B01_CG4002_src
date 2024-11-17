from bluepy.btle import Peripheral, DefaultDelegate
from bluepy.btle import BTLEDisconnectError
import time
import threading
import struct
from crc import Calculator, Crc16
import mqtt
import threading
import queue
import json
import random
import statistics
import pandas as pd
import logging

# create queues 
sub_queue = queue.Queue() # from ext
bullet_queue = queue.Queue() # from ext -> gun beetle
health_queue = queue.Queue() # from ext -> vest beetle
pub_queue = queue.Queue() # to ext
collate_queue = queue.Queue() # used for collating data from the different imu bluno threads -> pub_queue

# signal to allow collation to begin
setup_done_event = threading.Event()
setup_count = 0
setup_count_lock = threading.Lock()

# flag to restart bluno handshake if imu bluno stops sending data in the middle of an action
right_hand_flag = threading.Event()
right_leg_flag = threading.Event()

# handle logging to log file
logging.basicConfig(
        filename="../runtime.log",
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.ERROR
    )

# Fetch the player data from config.json
config = []
with open('config.json', 'r') as file:
    config = json.load(file)

FILE_PLAYER_ID = "2"
SELECTED_PLAYER = config[FILE_PLAYER_ID]["FILE_PLAYER"] # either "p1" or "p2"

# mac addresses for selected player
BLUNO_GATT_CHARACTERISTIC = "0000dfb1-0000-1000-8000-00805f9b34fb"
BLUNO_1_NAME = "RIGHT_HAND"
BLUNO_1_MAC = config[FILE_PLAYER_ID]["BLUNO_1_MAC"]
BLUNO_1_ID = 0x01

BLUNO_2_NAME = "GUN"
BLUNO_2_MAC = config[FILE_PLAYER_ID]["BLUNO_2_MAC"]
BLUNO_2_ID = 0x02

BLUNO_3_NAME = "RIGHT_LEG"
BLUNO_3_MAC = config[FILE_PLAYER_ID]["BLUNO_3_MAC"]
BLUNO_3_ID = 0x03

BLUNO_4_NAME = "VEST"
BLUNO_4_MAC = config[FILE_PLAYER_ID]["BLUNO_4_MAC"]
BLUNO_4_ID = 0x04

# used for printing colour on the terminal
colour_arr = {
    "RIGHT_HAND" : "\033[94m", # blue
    "GUN" : "\033[31m", # red
    "RIGHT_LEG" : "\033[32m", # green
    "VEST": "\033[33m" # yellow
}

# # create a dictionary of Blunos and their relevant attributes
bluno_dict = {
    "BLUNO_1": [BLUNO_1_NAME, BLUNO_1_MAC],
    "BLUNO_2": [BLUNO_2_NAME, BLUNO_2_MAC],
    "BLUNO_3": [BLUNO_3_NAME, BLUNO_3_MAC],
    "BLUNO_4": [BLUNO_4_NAME, BLUNO_4_MAC]
}

################# CREATE A 20 BYTE STRUCT

# # index for array in bluno dict
NAME = 0
ADDRESS = 1

# # array of threads created
threads_arr = []

# # PACKET FORMATS: ARDUINO -> LAPTOP
ACK_IN_FORMAT = "cBBc14sH" # char, uint8, uint8, char, char[14], uint16 # HEADER, INFO, SEQ. NUM, ACTION, PADDING, CRC
#IMU_IN_FORMAT = "cBB6H3sH" # char, uint8, uint8, 6 x uint16, char[3], uint16 # HEADER, INFO, SEQ. NUM, Ax, Ay, Az, Gx, Gy, Gz, PADDING, CRC
IMU_IN_FORMAT = "<2xB6h5x" # LE FORMAT: HEADER, INFO, SEQ. NUM, Ax, Ay, Az, Gx, Gy, Gz, PADDING, CRC
TRIGGER_IN_FORMAT = "cBB15sH" # char, uint8, uint8, char[15], uint16 # HEADER, INFO, SEQ. NUM, PADDING, CRC
HIT_IN_FORMAT = "cBB15sH" # char, uint8, uint8, char[15], uint16 # HEADER, INFO, SEQ. NUM, PADDING, CRC

# # PACKET FORMATS: LAPTOP -> ARDUINO
HANDSHAKE_OUT_FORMAT = "cBB15sH" # char, uint8, uint8, char[15], uint16 # HEADER, INFO, SEQ. NUM, PADDING, CRC
ACK_OUT_FORMAT = "cBBc14sH" # HEADER, INFO, SEQ. NUM, ACTION, PADDING, CRC
BULLET_UPDATE_OUT_FORMAT = "cBBB14s" # HEADER, INFO, SEQ. NUM, DATA, PADDING
HEALTH_UPDATE_OUT_FORMAT = "cBBB14s" # HEADER, INFO, SEQ. NUM, DATA, PADDING

# create delegate class for notification subscription
class MyDelegate(DefaultDelegate):
    def __init__(self, blunoInstance, name, characteristic, handshake_status):
        DefaultDelegate.__init__(self)
        self.name = name
        self.blunoInstance = blunoInstance
        self.buffer = []
        self.characteristic = characteristic
        self.bluno_seq_num = 0 # initialse bluno sequence num
        self.laptop_seq_num = 0
        self.isUpdateTransmissionComplete = True # flag for whether ack has been received after update packet was sent
        self.isHandshakeComplete = handshake_status
        self.start_time = time.time()
        self.num_corrupt_pkts = 0
        self.num_full_pkts = 0
        self.num_frag_pkts = 0
        self.pkt_time = time.time()

    def handleNotification(self, cHandle, data):
        self.buffer += data # ensure packets received are 20 bytes
        if len(self.buffer) >= 20:
            full_packet = self.buffer[:20] # extract out first 20 bytes
            self.num_full_pkts += 1
            self.buffer = self.buffer[20:] # reasssign buffer
            # Check CRC to ensure that data is not corrupted
            if checkCRC(full_packet):
                self.handleIncomingData(full_packet) # process data since crc is correct
                self.num_corrupt_pkts = 0 # reset corrupt counter once a proper packet is received
            else:
                print(f"corrupted data at {self.name}, packet dropped") # drop packet since crc is wrong
                self.num_corrupt_pkts += 1
                if self.num_corrupt_pkts == 3:
                    self.isHandshakeComplete = False # reinitiate handshake
                    self.num_corrupt_pkts = 0
                    self.buffer = [] # reset buffer when reinitiating handshake due to corruption
                    print(f"Multiple packets corrupted at {self.name}, restarting handshake...")
        else:
            # print(f"{colour_arr[self.name]}fragmented data: {data}, received at {self.name}{"\033[0m"}")
            self.num_frag_pkts += 1
    
    # This function is only called if the CRC is correct.
    # This function handles calling specific functions based on the packet header received
    def handleIncomingData(self, full_packet):
        # data is a list of 20 integers
        packet_header = chr(full_packet[0]) # extract and decode packet header
        received_seq_num = full_packet[2] # extract sequence number from incoming packet
        if self.isHandshakeComplete == False: # if handshake not done, wait for ACK0 from bluno
            if packet_header == 'A' and received_seq_num == 0:
                print(f"received ack 0 from {self.name}: {full_packet}")
                sendACKToBluno(self.blunoInstance, self.name, self.characteristic, 0)
                self.isHandshakeComplete = True
                self.bluno_seq_num = 0
                self.laptop_seq_num = 1
        else: # handshake has been done, proceed to process data accordingly
            if packet_header == 'A': # ack packet
                if received_seq_num == 0: # ack any residual handshake packets
                    print(f"received ack 0 from {self.name}: {full_packet}")
                    sendACKToBluno(self.blunoInstance, self.name, self.characteristic, 0)
                else: # ack for other packets
                    self.isUpdateTransmissionComplete = isMatchingReplyPacket(received_seq_num, self.laptop_seq_num)
                    if self.isUpdateTransmissionComplete:
                        self.laptop_seq_num = updateLaptopSequenceNumber(self.laptop_seq_num)
                    print(f"received ack from {self.name}: {full_packet}") # differentiate between handshake ack and message ack??? - use a different letter
                    # set flag here - this portion is entered when laptop sends an update packet and the bluno sends an ack
            elif packet_header == 'T': # trigger packet
                print(f"{time.time()-self.pkt_time}:{colour_arr[self.name]}Trigger data from {self.name}: {full_packet}{"\033[0m"}")
                self.pkt_time = time.time()
                self.bluno_seq_num = handleTriggerPacket(received_seq_num, self.bluno_seq_num)
                sendACKToBluno(self.blunoInstance, self.name, self.characteristic, self.bluno_seq_num) # stop and wait protocol, reliable protocol, ack should be sent with received sequence number
                logging.debug("Trigger")
            elif packet_header == 'I': # imu packet
                # print(f"IMU Data received from {self.name}. \nSpeed: {((self.num_full_pkts * 8 * 20) / (1000 * (time.time() - self.start_time))):.2f} kbps. \nfrag pkts: {(self.num_frag_pkts)}   full pkts: {self.num_full_pkts}   % frag: {self.num_frag_pkts/self.num_full_pkts * 100}")
                decodeIMUData(self.name, full_packet, received_seq_num) #, self.blunoInstance, self.characteristic) # no ack sent, unreliable protocol
            elif packet_header == 'S': # hit packet
                print(f"{colour_arr[self.name]}Hit data from {self.name}: {full_packet}{"\033[0m"}")
                self.bluno_seq_num = handleHitPacket(received_seq_num, self.bluno_seq_num)
                sendACKToBluno(self.blunoInstance, self.name, self.characteristic, self.bluno_seq_num) # stop and wait protocol, reliable protocol
                logging.debug("Hit")
            else: # all other types of notifications
                print(f"Notification from {self.name}: {full_packet}")


# create bluno thread class to run a bluno communication instance on a thread
# creating a class to run a thread: https://stackoverflow.com/questions/23100704/running-infinite-loops-using-threads-in-python
class BlunoThread(threading.Thread):
    def __init__(self, address, name):
        threading.Thread.__init__(self)
        self.address = address
        self.name = name
        # self.Peripheral = None
        self.running = True
        self.reconnection_counter = 0
        self.connected = False
        self.characteristic = None
        self.handshake = False

    def run(self):
        global setup_count
        while self.running:
            try: 
                # handle connection & subscription in the outer while loop to be able to reconnect to the Bluno during disconnection
                blunoInstance = Peripheral(self.address) # connect
                print(f"connected to {self.name}")
                self.characteristic = blunoInstance.getCharacteristics(uuid=BLUNO_GATT_CHARACTERISTIC)[0]
                delegate = MyDelegate(blunoInstance, self.name, self.characteristic, self.handshake)
                blunoInstance.setDelegate(delegate) # subscribe to notifications
                print(f"subscribed to {self.name}")
                self.connected = True
                # keep sending handshake after timeout till ack received from bluno
                handshake_start_time = 0
                while self.running:
                    while not self.handshake:
                        # sendHandshakeToBluno(blunoInstance, self.name, self.characteristic)
                        if time.time() - handshake_start_time > 2: # resend handshake if it has been more than 2s since last handshake was sent
                            sendHandshakeToBluno(blunoInstance, self.name, self.characteristic)
                            handshake_start_time = time.time()
                        if blunoInstance.waitForNotifications(1.0): # listen to notifications
                            if not blunoInstance.delegate.isHandshakeComplete:
                                continue
                            else:
                                self.handshake = blunoInstance.delegate.isHandshakeComplete # set handshake to true
                    print(f"handshake with {self.name} completed at {time.time()}")
                    with setup_count_lock:
                        if self.name == "RIGHT_HAND" or self.name == "RIGHT_LEG":
                            setup_count += 1
                            print(f"after {self.name}, current count: {setup_count}...")
                            if setup_count == 2: # change this depending on the number of blunos to connect before recording data
                                setup_done_event.set()
                    # main loop
                    while self.handshake: 
                        if blunoInstance.waitForNotifications(1.0): # listen to notifications
                            self.handshake = blunoInstance.delegate.isHandshakeComplete # check if there is a need to reinitiate handshake
                            if not self.handshake: # multiple corrupt packets received in a row
                                break # break out of inner loop to then rehandle handshake
                        if not sub_queue.empty(): # if there is data from ext, put the health and bullet data in the respective queues
                            data_from_ext = sub_queue.get() # fetch json data from ext comms
                            data_from_ext_dict = json.loads(data_from_ext)
                            print(data_from_ext_dict)
                            try:
                                if data_from_ext_dict[SELECTED_PLAYER]["action"] == "update":
                                    health_data = data_from_ext_dict[SELECTED_PLAYER]["hp"]
                                    health_queue.put(health_data)
                                    bullet_data = data_from_ext_dict[SELECTED_PLAYER]["bullets"]
                                    bullet_queue.put(bullet_data)
                            except KeyError as e:
                                print("Key error")
                                print(e)
                        if self.name == "GUN" and not bullet_queue.empty(): # if the thread belongs to the gun beetle and there is a bullet update, process it
                            packet_data = bullet_queue.get()
                            packet_send_start_time = 0
                            blunoInstance.delegate.isUpdateTransmissionComplete = False
                            while not blunoInstance.delegate.isUpdateTransmissionComplete and blunoInstance.delegate.isHandshakeComplete:
                                if time.time() - packet_send_start_time > 1.5: # timeout till next packet is sent
                                    sendBulletUpdatePacket(self.name, self.characteristic, packet_data, blunoInstance.delegate.laptop_seq_num)
                                    packet_send_start_time = time.time()
                                if blunoInstance.waitForNotifications(1.0): # listen to notifications
                                    continue
                            if not blunoInstance.delegate.isHandshakeComplete:
                                self.handshake = blunoInstance.delegate.isHandshakeComplete
                                break
                        elif self.name == "VEST" and not health_queue.empty(): # if the thread belongs to the vest beetle and there is a health update, process it
                            packet_data = health_queue.get()
                            packet_send_start_time = 0
                            blunoInstance.delegate.isUpdateTransmissionComplete = False
                            while not blunoInstance.delegate.isUpdateTransmissionComplete and blunoInstance.delegate.isHandshakeComplete: #
                                if time.time() - packet_send_start_time > 1.5: # timeout till next packet is sent
                                    sendHealthUpdatePacket(self.name, self.characteristic, packet_data, blunoInstance.delegate.laptop_seq_num)
                                    packet_send_start_time = time.time()
                                if blunoInstance.waitForNotifications(1.0): # listen to notifications
                                    continue
                            if not blunoInstance.delegate.isHandshakeComplete:
                                self.handshake = blunoInstance.delegate.isHandshakeComplete
                                break
                        elif self.name == "RIGHT_HAND" and right_hand_flag.is_set():
                            blunoInstance.delegate.isHandshakeComplete = False
                            self.handshake = False
                            right_hand_flag.clear()
                        elif self.name == "RIGHT_LEG" and right_leg_flag.is_set():
                            blunoInstance.delegate.isHandshakeComplete = False
                            self.handshake = False
                            right_leg_flag.clear()
            except BTLEDisconnectError:
                if self.connected == True: # just got disconnected
                    print(f"disconnected from {self.name}")
                    self.connected = False
                    self.handshake = False
                else: # reconnection timer timed out
                    print(f"reconnection to {self.name} timed out")
                print(f"reconnection counter: {self.reconnection_counter}. Attempting to reconnect to {self.name}")
                self.reconnection_counter += 1

    def stop(self):
        self.running = False
        # if self.Peripheral:
        #         self.Peripheral.disconnect()

# Resets sequence number on bluno
# This function is meant to indicate to the bluno to re-initiate connection and transmission
def sendHandshakeToBluno(blunoInstance, name, characteristic):
    HANDSHAKE_FORMAT = "cBB15s"
    payload = struct.pack(HANDSHAKE_FORMAT, b"H", 0x01, 0, b"zzzzzzzzzzzzzz") # TODO: MATCH DEVICE ID
    payload_with_crc = createPayloadWithCRC(payload)
    characteristic.write(payload_with_crc)
    print(f"begin handshake with {name}...")

def sendACKToBluno(blunoInstance, name, characteristic, seq_num):
    ACK_FORMAT = "cBBc14s" # char1, int1, char1, 14char1
    payload = struct.pack(ACK_FORMAT, b"A", 0x01, seq_num, b"A", b"zzzzzzzzzzzzz")
    payload_with_crc = createPayloadWithCRC(payload)
    characteristic.write(payload_with_crc)
    print(f"sent ack {seq_num} to {name}...")

def createPayloadWithCRC(payload):
    calculator = Calculator(Crc16.MODBUS)
    createCRC = calculator.checksum(payload)
    payload_with_crc = payload + createCRC.to_bytes(2, "big") # big endian format
    return payload_with_crc


def checkCRC(packet):
    # extract last two bytes [upper, lower]
    upper, lower = packet[18], packet[19]
    receivedCRCValue = upper * 256 + lower
    receivedPayload = bytes(packet[:18]) # retrieve first 18 values
    calculator = Calculator(Crc16.MODBUS)
    return receivedCRCValue == calculator.checksum(receivedPayload)


# This function processes IMU packets sent by the Bluno.
# The format for the IMU packet is as follows:
    # HEADER[0], INFO[1], SEQ. NUM[2], Ax[3:4], Ay[5:6], Az[7:8], Gx[9:10], Gy[11:12], Gz[13:14], PADDING[15:17], CRC[18:19]
# Bluno sends the A & G values in Little Endian format -> needs to be converted
def decodeIMUData(name, packet, seq_num): #, blunoInstance, characteristic):
    seq_num, Ax, Ay, Az, Gx, Gy, Gz = struct.unpack(IMU_IN_FORMAT, bytes(packet))
    arr = [name, Ax, Ay, Az, Gx, Gy, Gz]
    if setup_done_event.is_set(): # only put data into the queue once all blunos are connected
        collate_queue.put(arr)

def handleTriggerPacket(received_seq_num, bluno_seq_num):
    if bluno_seq_num < 255:
        if bluno_seq_num+1 == received_seq_num:
            putDataToPubQueue(FILE_PLAYER_ID,"gun", []) # change player id
            return bluno_seq_num + 1
    elif bluno_seq_num == 255:
        if received_seq_num == 1:
            putDataToPubQueue(FILE_PLAYER_ID,"gun", []) # change player id
            bluno_seq_num = 1
            return bluno_seq_num
    return bluno_seq_num # no update to bluno sequence number if received sequence number is out of order

def handleHitPacket(received_seq_num, bluno_seq_num):
    if bluno_seq_num < 255:
        if bluno_seq_num+1 == received_seq_num:
            putDataToPubQueue(FILE_PLAYER_ID,"hit", []) # change player id
            return bluno_seq_num + 1
    elif bluno_seq_num == 255:
        if received_seq_num == 1:
            putDataToPubQueue(FILE_PLAYER_ID,"hit", []) # change player id
            bluno_seq_num = 1
            return bluno_seq_num
    return bluno_seq_num # no update to bluno sequence number if received sequence number is out of order

def putDataToPubQueue(player_id, action, data):
    pub_queue.put(
        json.dumps(
            {
                "topic": "default",
                "payload": json.dumps(
                    {
                        "player_id": player_id,
                        "action": action,
                        "data": data,
                    }
                ),
            }
        )
    )

def sendBulletUpdatePacket(name, characteristic, bullet_count, laptop_seq_num):
    payload = struct.pack(BULLET_UPDATE_OUT_FORMAT, b"B", 0x01, laptop_seq_num, bullet_count, b"zzzzzzzzzzzzz")
    payload_with_crc = createPayloadWithCRC(payload)
    characteristic.write(payload_with_crc)
    print(f"sent bullet update {laptop_seq_num} to {name}...")

def sendHealthUpdatePacket(name, characteristic, health_count, laptop_seq_num):
    payload = struct.pack(HEALTH_UPDATE_OUT_FORMAT, b"X", 0x01, laptop_seq_num, health_count, b"zzzzzzzzzzzzz")
    payload_with_crc = createPayloadWithCRC(payload)
    characteristic.write(payload_with_crc)
    print(f"sent health update {laptop_seq_num} to {name}...")
    
def isMatchingReplyPacket(received_seq_num, laptop_seq_num):
    if received_seq_num == laptop_seq_num:
        return True
    return False # received ack seq number does not match seq num of packet sent

def updateLaptopSequenceNumber(laptop_seq_num):
    if laptop_seq_num < 255:
        return laptop_seq_num + 1
    elif laptop_seq_num == 255:
        return 1
    return laptop_seq_num


def consumerThread():
    count_csv = 0
    print(f"{setup_done_event} done")
    isFullCycleComplete = False # do not perform if one full iteration is complete
    isCollate = False # flag to determine if data should be collated
    # flags to determine if bluno has collected max samples for action
    is_right_hand_bluno_complete = False
    is_right_leg_bluno_complete = False
    # number of samples to collect after start of move has been detected
    max_iter = 80
    # data format: [time.time(), name, Ax, Ay, Az, Gx, Gy, Gz, seq_num]
    # arrays to store 80 samples
    full_right_hand_coll_arr = []
    full_right_leg_coll_arr = []
    # arrays to store 5 samples
    prev_right_hand_mini_arr = []
    prev_right_leg_mini_arr = []
    curr_right_hand_mini_arr = []
    curr_right_leg_mini_arr = []
    while(not isFullCycleComplete): # while one full collation + output iteration is not complete
        if not isCollate:
            pkt = collate_queue.get()
            name = pkt[0]
            data = pkt[1:]
            match name:
                case "RIGHT_HAND":
                    if len(prev_right_hand_mini_arr) < 5:
                        prev_right_hand_mini_arr.append(data)
                    elif len(curr_right_hand_mini_arr) < 5:
                        curr_right_hand_mini_arr.append(data)
                    else:
                        # compare data 
                        if isAboveThreshold(name, prev_right_hand_mini_arr, curr_right_hand_mini_arr):
                            isCollate = True # remember to clear the arrays !!!
                            print(f"{name} CROSSED THRESHOLD")
                        else:
                            prev_right_hand_mini_arr = prev_right_hand_mini_arr[1:5]
                            prev_right_hand_mini_arr.append(curr_right_hand_mini_arr[0])
                            curr_right_hand_mini_arr = curr_right_hand_mini_arr[1:5]
                case "RIGHT_LEG":
                    if len(prev_right_leg_mini_arr) < 5:
                        prev_right_leg_mini_arr.append(data)
                    elif len(curr_right_leg_mini_arr) < 5:
                        curr_right_leg_mini_arr.append(data)
                    else:
                        # compare data 
                        if isAboveThreshold(name, prev_right_leg_mini_arr, curr_right_leg_mini_arr):
                            isCollate = True # remember to clear the arrays !!!
                            print(f"{name} CROSSED THRESHOLD")
                        else:
                            prev_right_leg_mini_arr = prev_right_leg_mini_arr[1:5]
                            prev_right_leg_mini_arr.append(curr_right_leg_mini_arr[0])
                            curr_right_leg_mini_arr = curr_right_leg_mini_arr[1:5]
        else: # put all data into the collation queue
            isSent = False
            print("STARTED DATA COLLATION")
            collation_start_time = time.time() # start timer for when data collation happens
            full_right_hand_coll_arr  = curr_right_hand_mini_arr # initialise array with 5 values
            full_right_leg_coll_arr  = curr_right_leg_mini_arr 
            while (time.time() - collation_start_time < 4): # stay in loop for 5s since start of action
                while(not is_right_hand_bluno_complete or not is_right_leg_bluno_complete):
                    if time.time() - collation_start_time > 4:
                        logging.error("Bluno stoped sending data")
                        right_hand_flag.set()
                        right_leg_flag.set()
                        break
                    pkt = collate_queue.get()
                    name = pkt[0]
                    data = pkt[1:]
                    match name:
                        case "RIGHT_HAND":
                            if len(full_right_hand_coll_arr) < max_iter:
                                full_right_hand_coll_arr.append(data)
                            else:
                                is_right_hand_bluno_complete = True
                        case "RIGHT_LEG":
                            if len(full_right_leg_coll_arr) < max_iter:
                                full_right_leg_coll_arr.append(data)
                            else:
                                is_right_leg_bluno_complete = True
                # send data to external comms only once during the 5s after data is collated
                if not isSent and is_right_hand_bluno_complete and is_right_leg_bluno_complete:
                    pub_queue.put(
                        json.dumps(
                            {
                                "topic": "default",
                                "payload": json.dumps(
                                    {
                                        "player_id": FILE_PLAYER_ID,
                                        "action": "data",
                                        "data": [full_right_hand_coll_arr, full_right_leg_coll_arr],
                                    }
                                ),
                            }
                        )
                    )
                    isSent = True
            
            # # write data collated into a csv
            # action_arr = ["basketball", "bowling", "logout", "rainbomb", "reload_left", "reload_right", "shield", "soccer", "volleyball"]
            # action = action_arr[0]
            # csv_header_arr = ["time", "name", "Ax", "Ay", "Az", "Gx", "Gy", "Gz", "seq_num"]
            # bluno_1_df = pd.DataFrame(full_right_hand_coll_arr)
            # bluno_1_df.to_csv(path_or_buf=f"../action_data/{action}/right_hand{count_csv}.csv", index=False, header=csv_header_arr)
            # bluno_3_df = pd.DataFrame(full_right_leg_coll_arr)
            # bluno_3_df.to_csv(path_or_buf=f"../action_data/{action}/right_leg{count_csv}.csv", index=False, header=csv_header_arr)

            # after collation is complete
            # reset all arrays
            full_right_hand_coll_arr = []
            full_right_leg_coll_arr = []
            prev_right_hand_mini_arr = []
            prev_right_leg_mini_arr = []
            curr_right_hand_mini_arr = []
            curr_right_leg_mini_arr = []
            # reset flags
            isCollate = False
            is_right_hand_bluno_complete = False
            is_right_leg_bluno_complete = False
            print(F"collation {count_csv} complete")
            # isFullCycleComplete = True # set flag after one full iteration is complete and the data has been output -> prevent overwriting
            count_csv += 1
            with collate_queue.mutex:
                collate_queue.queue.clear()


def isAboveThreshold(name, prev_arr, curr_arr):
    if name == "RIGHT_LEG":
        FIXED_THRESHOLD = 40000
    else:
        FIXED_THRESHOLD = 20000

    AX_INDEX = 0
    AY_INDEX = 1
    AZ_INDEX = 2
    GX_INDEX = 3
    GY_INDEX = 4
    GZ_INDEX = 5

    total_prev_Ax = 0
    total_prev_Ay = 0
    total_prev_Az = 0
    total_prev_Gx = 0
    total_prev_Gy = 0
    total_prev_Gz = 0

    # populate mean_prev_X
    for data in prev_arr:
        total_prev_Ax += data[AX_INDEX]
        total_prev_Ay += data[AY_INDEX]
        total_prev_Az += data[AZ_INDEX]
        total_prev_Gx += data[GX_INDEX]
        total_prev_Gy += data[GY_INDEX]
        total_prev_Gz += data[GZ_INDEX]
    
    mean_prev_Ax = total_prev_Ax / 5
    mean_prev_Ay = total_prev_Ay / 5
    mean_prev_Az = total_prev_Az / 5
    mean_prev_Gx = total_prev_Gx / 5
    mean_prev_Gy = total_prev_Gy / 5
    mean_prev_Gz = total_prev_Gz / 5

    total_curr_Ax = 0
    total_curr_Ay = 0
    total_curr_Az = 0
    total_curr_Gx = 0
    total_curr_Gy = 0
    total_curr_Gz = 0

    # populate mean_curr_X
    for data in curr_arr:
        total_curr_Ax += data[AX_INDEX]
        total_curr_Ay += data[AY_INDEX]
        total_curr_Az += data[AZ_INDEX]
        total_curr_Gx += data[GX_INDEX]
        total_curr_Gy += data[GY_INDEX]
        total_curr_Gz += data[GZ_INDEX]
    
    mean_curr_Ax = total_curr_Ax / 5
    mean_curr_Ay = total_curr_Ay / 5
    mean_curr_Az = total_curr_Az / 5
    mean_curr_Gx = total_curr_Gx / 5
    mean_curr_Gy = total_curr_Gy / 5
    mean_curr_Gz = total_curr_Gz / 5
    
    # compare threshold
    diff_Ax = abs(mean_curr_Ax-mean_prev_Ax)
    diff_Ay = abs(mean_curr_Ay-mean_prev_Ay)
    diff_Az = abs(mean_curr_Az-mean_prev_Az)
    diff_Gx = abs(mean_curr_Gx-mean_prev_Gx)
    diff_Gy = abs(mean_curr_Gy-mean_prev_Gy)
    diff_Gz = abs(mean_curr_Gz-mean_prev_Gz)

    max_diff = max(diff_Ax, diff_Ay, diff_Az ,diff_Gx, diff_Gy, diff_Gz)

    return max_diff > FIXED_THRESHOLD

def createBlunoThreads():
    for bluno in bluno_dict:
        name = bluno_dict[bluno][NAME]
        address = bluno_dict[bluno][ADDRESS]
        thread = BlunoThread(address, name)
        thread.start()
        threads_arr.append(thread)
                
if __name__ == '__main__':
    try:
        publisher = mqtt.MqttPublisher(pub_queue)
        publisher_thread = threading.Thread(target=publisher.begin, daemon=True)
        publisher_thread.start()
        threads_arr.append(publisher_thread)
        threshold_thread = threading.Thread(target=consumerThread)
        threshold_thread.start()
        threads_arr.append(threshold_thread)
        # Create and start the MQTT subscriber thread
        subscriber = mqtt.MqttSubscriber(sub_queue)
        subscriber_thread = threading.Thread(target=subscriber.begin, daemon=True)
        subscriber_thread.start()
        threads_arr.append(subscriber_thread)
        createBlunoThreads()

    except KeyboardInterrupt:
        if threads_arr:
            print("shutting down threads...")
            for thread in threads_arr:
                thread.stop()
                thread.join()
        print("program terminated...")
    except Exception as e:
        print(e)



