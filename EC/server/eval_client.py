import base64
import random
import os
import socket
import threading
import queue
import json
import mqtt
import time
import errno
from printer import log, THREAD
from enums import Action


from GameState import GameState

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import timeout_checker

SERVER_PORT = 8888

AI_HOST = "127.0.0.1"
AI_PORT = 65433

ENABLE_AI = True
CHECK_VISIBILITY = False
USE_HEARTBEAT = True

TWO_PLAYER = True

ENABLE_SEND_GAME_STATE = True
ENABLE_FREE_PLAY = False

ENABLE_BLOCK_USER = True

# if logout can happen from round 23 onwards, this should be 22.
# 1-indexed
if TWO_PLAYER:
    ROUNDS_BEFORE_LOGOUT = 41
else:
    ROUNDS_BEFORE_LOGOUT = 21

GUN_TIMEOUT_SECONDS = 2


class EvalClient:
    def __init__(
        self,
        server_address,
        server_port,
        secret_key,
        message_queue,
        vis_message_queue,
        checker: timeout_checker.TimeoutChecker,
        delayed_message_queue,
    ):
        self.server_address = server_address
        self.server_port = server_port
        self.secret_key = secret_key

        if not ENABLE_FREE_PLAY:
            self.socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )  # TCP socket connecting to the eval client
            self.socket.settimeout(2.0)  # 2 second timeout
            self.socket.bind(("", 0))

        self.message_queue = message_queue
        self.vis_message_queue = vis_message_queue
        self.delayed_message_queue = delayed_message_queue
        self.timeout_checker = checker

        # TODO: handle if we restart halfway?
        self.current_round = 1
        self.error_rounds = 0

        if ENABLE_AI:

            self.ai_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ai_socket.settimeout(7.0)
            self.ai_socket.connect((AI_HOST, AI_PORT))

        self.game_state = GameState()
        self.pending_query = None
        self.last_gun = {"1": 0, "2": 0}
        self.last_hit = {"1": 0, "2": 0}
        # at start of game p1 is at quadrant 1 and p2 is at quadrant 3, so should be visible
        self.can_see_opponent = {"1": True, "2": True}
        self.rain_count = {"1": 0, "2": 0}
        self.blocked_users = {"1": False, "2": False}

    # returns NON-UTF8 ciphertext
    def encrypt_message(self, message):
        # Convert secret key to bytes
        secret_key_bytes = bytes(str(self.secret_key), encoding="utf8")

        # Generate a random IV (Initialization Vector)
        iv = os.urandom(AES.block_size)

        # Create AES cipher object using the secret key and IV in CBC mode
        cipher = AES.new(secret_key_bytes, AES.MODE_CBC, iv)

        # Pad the message to make its length a multiple of AES block size
        padded_message = pad(message.encode("utf8"), AES.block_size)

        # Encrypt the message
        encrypted_message = cipher.encrypt(padded_message)

        # Combine IV with encrypted message and encode with base64
        cipher_text = base64.b64encode(iv + encrypted_message).decode("utf-8")
        return cipher_text

    def connect(self):
        if ENABLE_FREE_PLAY:
            log(THREAD.EVAL, "FREE PLAY, SKIPPING EVAL SERVER CONNECTION")
            return
        # encrypt hello
        cipher_text = self.encrypt_message("hello")
        # build message
        msg = f"{len(cipher_text)}_{cipher_text}"
        # make request to server as specified in init
        # Connect to the server at the specified address and port
        self.socket.connect((self.server_address, self.server_port))

        log(
            THREAD.EVAL,
            f"client: connected to {self.server_address} on port {self.server_port}",
        )

        self.socket.sendall(msg.encode("utf-8"))
        log(THREAD.EVAL, f"client: sent: {msg}")

    def get_player_data(self, player_id: str):
        """
        expects either "1" or "2"
        """
        if player_id not in ["1", "2"]:
            raise Exception(f"get_player_data: unknown player id {player_id}")
        return self.game_state.get_dict()[f"p{player_id}"]

    def get_opponent(self, player_id: str) -> str:
        return "1" if player_id == "2" else "2"

    def process_messages(self):
        """
        Function to process messages from the subscriber queue.
        """
        while True:
            # Block until a message is available
            message = self.message_queue.get()
            if message is None:
                break
            try:
                parsed_msg = json.loads(message)
            except Exception:

                log(THREAD.EVAL, "client: ERROR invalid message")
                log(THREAD.EVAL, message)
                continue
            if not isinstance(parsed_msg, dict):
                log(THREAD.EVAL, f"client: ERROR message is not dict {parsed_msg}")
                continue
            action = parsed_msg["action"]
            player_id = str(parsed_msg["player_id"])
            data = parsed_msg.get("data", "")
            bomb_count_input = parsed_msg.get("bomb_count", 0)
            is_visible = parsed_msg.get("is_visible", False)
            self.handle_message(action, player_id, data, bomb_count_input, is_visible)

    def handle_message(self, action, player_id, data, bomb_count_input, is_visible):
        curr_time = time.time()
        opponent_id = self.get_opponent(player_id)
        can_see_opponent = False

        is_blocking_action = action not in ["hit", "heartbeat", "gun_miss"]

        # only "heartbeat", "hit" and "gun_miss" are not affected by the block
        if ENABLE_BLOCK_USER:
            if is_blocking_action:
                if self.blocked_users[player_id]:
                    log(THREAD.EVAL, f"DROPPING ACTION FROM BLOCKED USER {player_id}")
                    return

        if action == "data":
            if ENABLE_AI:
                try:
                    action = self.send_to_ai(json.dumps(data), True)
                    log(THREAD.EVAL, f"client: AI RESPONSE: {action}")
                    if action is None:
                        return
                except Exception as e:
                    log(THREAD.EVAL, f"client: exception from AI {e}")
                    return
            else:
                # not needed if AI is not enabled
                return

        if action == "dummy":
            actions = [
                # "gun",
                "shield",
                # "bomb",
                "reload",
                "basket",
                "soccer",
                "volley",
                "bowl",
            ]
            action = random.choice(actions)

        if action == "heartbeat":
            self.can_see_opponent[player_id] = is_visible
            self.rain_count[opponent_id] = bomb_count_input
            return

        if action == "hit":
            return

        if action == "logout":
            if not ENABLE_FREE_PLAY and self.current_round < ROUNDS_BEFORE_LOGOUT:
                log(
                    THREAD.EVAL,
                    f"client: current round {self.current_round}, cannot logout before {ROUNDS_BEFORE_LOGOUT}",
                )
                return

        if is_blocking_action:
            self.blocked_users[player_id] = True
            log(THREAD.EVAL, f"blocking user {player_id} until next action")
            if (
                self.blocked_users[player_id] is True
                and self.blocked_users[opponent_id] is True
            ):
                self.blocked_users[player_id] = False
                self.blocked_users[opponent_id] = False

        if action in [
            "bomb",
            "basket",
            "volley",
            "soccer",
            "bowl",
        ]:
            if CHECK_VISIBILITY:
                self.pending_query = action
                # query the visualizer
                self.vis_message_queue.put(
                    json.dumps(
                        {
                            "topic": "player1",
                            "payload": json.dumps(
                                {f"p{player_id}": {"action": "query"}}
                            ),
                        }
                    )
                )
                return
            if USE_HEARTBEAT:
                can_see_opponent = self.can_see_opponent[player_id]
            else:
                can_see_opponent = True

        # Used if CHECK_VISIBILITY is true
        if action == "query_resp":
            if self.pending_query:
                action = self.pending_query
                self.pending_query = None
                can_see_opponent = is_visible
            else:
                return

        if action == "gun":
            opponent_id = self.get_opponent(player_id)
            log(
                THREAD.EVAL,
                f"gun received at {curr_time}",
            )
            can_see_opponent = self.can_see_opponent[player_id]

        if TWO_PLAYER:
            self.perform_action(
                player_id, action, self.rain_count[opponent_id], can_see_opponent
            )

        else:
            position_1 = 1
            position_2 = 1
            no_visualiser = False
            self.game_state.perform_action(
                action,
                int(player_id),
                position_1,
                position_2,
                no_visualiser,
            )

        if ENABLE_SEND_GAME_STATE:
            self.send_game_state(
                action=action, player_id=player_id, can_see_opponent=can_see_opponent
            )

    def perform_action(self, player_id, action, bomb_count, is_visible):
        """
        is_visible should be true for gun if the hit is very close to the previous gun

        return game state and messages to send

        data = dict()
        data['hp']              = self.hp
        data['bullets']         = self.num_bullets
        data['bombs']           = self.num_bombs
        data['shield_hp']       = self.hp_shield
        data['deaths']          = self.num_deaths
        data['shields']         = self.num_shield
        return data
        """
        attacker = self.game_state.player_1
        opponent = self.game_state.player_2
        if player_id == "2":
            attacker = self.game_state.player_2
            opponent = self.game_state.player_1
        # do rain_bomb damage
        dmg_per_rain = 5
        if bomb_count > 0:
            log(
                THREAD.EVAL,
                f"applying {bomb_count * dmg_per_rain} RAIN DAMAGE to {self.get_opponent(player_id)}",
            )
            opponent.reduce_health(bomb_count * dmg_per_rain)

        if action == "gun":
            attacker.shoot(opponent, is_visible)
        elif action == "shield":
            attacker.shield()
        elif action == "reload":
            attacker.reload()
        elif action == "bomb":
            # check the ammo
            if attacker.num_bombs <= 0:
                return
            attacker.num_bombs -= 1

            # check if the opponent is visible
            if not is_visible:
                # this bomb will not start a rain and hence has no effect with respect to gameplay
                return
            opponent.reduce_health(dmg_per_rain)
        elif action in {"basket", "soccer", "volley", "bowl"}:
            # all these have the same behaviour
            attacker.harm_AI(opponent, is_visible)
        elif action == "logout":
            # has no change in game state
            pass
        else:
            # invalid action we do nothing
            pass

    def receive_data(self) -> bytes:
        buffer = b""  # Holds the incoming data chunks
        data_length = None  # Length of the full data

        while True:
            chunk = self.socket.recv(1024)
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

    def send_game_state(self, action, player_id, can_see_opponent):
        """
        send_game_state sends the current game state to the eval_server, visualizers and relay nodes
        """
        player_msg = {
            "player_id": player_id,
            "action": action,
            "game_state": self.game_state.get_dict(),
        }
        self.current_round += 1
        if not ENABLE_FREE_PLAY:
            try:

                # send to eval_server
                cipher_text = self.encrypt_message(json.dumps(player_msg))
                msg = f"{len(cipher_text)}_{cipher_text}"
                self.socket.sendall(msg.encode("utf-8"))

                # fix for case where wrong game state is stored
                # usually triggered when an action is sent when users are still changing positions
                while self.error_rounds > 0:
                    resp = self.receive_data()
                    log(
                        THREAD.EVAL,
                        f"game errors remaining: {self.error_rounds}, resp: {resp}",
                    )
                    self.error_rounds -= 1

                # Receive response from the server
                ## PACKET FRAGMENTATION HANDLING
                response = self.receive_data()
            except socket.timeout:
                log(THREAD.EVAL, "SOCKET TIMEOUT, MOST LIKELY DUPLICATE MESSAGE")
                self.error_rounds += 1
                return

        attacker_payload = {}
        opponent_payload = {}
        if TWO_PLAYER:
            opponent_id = self.get_opponent(player_id)
            attacker_payload = self.get_player_data(player_id)
            opponent_payload = self.get_player_data(opponent_id)
            attacker_payload["action"] = action
            opponent_payload["action"] = "update"
            if can_see_opponent:
                if action == "gun":
                    opponent_payload["action"] = "hit"
                if action in ["volley", "bowl", "soccer", "basket", "bomb"]:
                    opponent_payload["action"] = f"{action}_hit"
        else:
            attacker_payload = self.get_player_data("1")
            attacker_payload["action"] = action
            opponent_payload = self.get_player_data("2")
            opponent_payload["action"] = "update"

        attacker_payload["kills"] = opponent_payload["deaths"]
        opponent_payload["kills"] = attacker_payload["deaths"]
        payload = {
            f"p{player_id}": attacker_payload,
            f"p{opponent_id}": opponent_payload,
        }
        self.vis_message_queue.put(
            json.dumps(
                {
                    "topic": "player1",
                    "payload": json.dumps(payload),
                }
            )
        )

        # Update game state to match the response from the eval server
        if not ENABLE_FREE_PLAY:
            log(THREAD.EVAL, f"response from eval server: {response}")
            resp_json = json.loads(response)
            p1_json = resp_json["p1"]
            p2_json = resp_json["p2"]
            diff_msg = self.game_state.difference(resp_json)
            log(THREAD.EVAL, diff_msg)
            if diff_msg != "Game state difference : {'p1': {}, 'p2': {}}":
                self.game_state.player_1.set_state(
                    p1_json["bullets"],
                    p1_json["bombs"],
                    p1_json["hp"],
                    p1_json["deaths"],
                    p1_json["shields"],
                    p1_json["shield_hp"],
                )
                self.game_state.player_2.set_state(
                    p2_json["bullets"],
                    p2_json["bombs"],
                    p2_json["hp"],
                    p2_json["deaths"],
                    p2_json["shields"],
                    p2_json["shield_hp"],
                )
                p1_payload = self.game_state.get_dict()["p1"]
                p1_payload["action"] = "update"
                p2_payload = self.game_state.get_dict()["p2"]
                p2_payload["action"] = "update"
                p1_payload["kills"] = p2_payload["deaths"]
                p2_payload["kills"] = p1_payload["deaths"]
                payload = {"p1": p1_payload, "p2": p2_payload}
                self.vis_message_queue.put(
                    json.dumps(
                        {
                            "topic": "player1",
                            "payload": json.dumps(payload),
                        }
                    )
                )
        return

    def send_to_ai(self, data: str, retry: bool) -> str:
        try:

            n = len(data)
            to_send = f"{n}_{data}".encode()
            for i in range(0, n, 2048):
                log(THREAD.EVAL, f"Client sending data: {i}:{i + 2048}")
                self.ai_socket.sendall(to_send[i : i + 2048])

            response = self.ai_socket.recv(2048)  # Receive response from the server
            log(THREAD.EVAL, f"response from AI: {response.decode()}")
            parsed = json.loads(response)

            log(THREAD.EVAL, f"parsed response from AI: {parsed}")
            # get the action from AI
            if len(parsed) == 0:
                raise Exception("empty response from AI")
            else:
                action = Action.from_int(parsed[0])
            # Send 'END' to signal termination
            # s.sendall(b"END")
            return action
        except socket.error as e:
            if e.errno != errno.EPIPE:
                # Not a broken pipe
                raise e
            if retry:
                if self.ai_socket:
                    self.ai_socket.close()
                self.ai_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.ai_socket.settimeout(7.0)
                self.ai_socket.connect((AI_HOST, AI_PORT))
                return self.send_to_ai(data, False)
        except Exception as e:
            log(THREAD.EVAL, f"error getting data from AI: {e}")


# Create a thread-safe queue
message_queue = queue.Queue()
vis_message_queue = queue.Queue()
delayed_message_queue = queue.Queue()


def clear():

    # for windows
    if os.name == "nt":
        _ = os.system("cls")

    # for mac and linux(here, os.name is 'posix')
    else:
        _ = os.system("clear")


def main():
    server_address = "127.0.0.1"
    secret_key = "passwordpassword"

    # Keep the main thread alive while the worker threads are running
    try:
        clear()

        checker = timeout_checker.TimeoutChecker(
            in_queue=delayed_message_queue, out_queue=message_queue
        )
        checker_thread = threading.Thread(target=checker.begin, daemon=True)
        checker_thread.start()

        # Create and start the MQTT subscriber thread
        subscriber = mqtt.MqttSubscriber(message_queue)
        subscriber_thread = threading.Thread(target=subscriber.begin, daemon=True)
        subscriber_thread.start()

        publisher = mqtt.MqttPublisher(vis_message_queue)
        publisher_thread = threading.Thread(target=publisher.begin, daemon=True)
        publisher_thread.start()

        # from_ai_queue, to_ai_queue = ai_wrapper.init_ai_comms()
        c = EvalClient(
            server_address,
            SERVER_PORT,
            secret_key,
            message_queue,
            vis_message_queue,
            checker,
            delayed_message_queue,
        )

        c.connect()
        c.process_messages()
    except KeyboardInterrupt:
        print("Shutting down...")
        message_queue.put(None)  # Stop signal for the message processor thread
        vis_message_queue.put(None)
        delayed_message_queue.put(None)
        checker_thread.join()
        subscriber_thread.join()
        publisher_thread.join()


if __name__ == "__main__":
    main()
