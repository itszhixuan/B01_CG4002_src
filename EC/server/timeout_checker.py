import threading
import queue
import json
from typing import Optional
import time


class TimeoutChecker:
    def __init__(self, in_queue, out_queue):
        self.flag = False
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.current_messages = {}

    def set_flag(self, value: bool) -> None:
        """Set the flag value thread-safely."""
        with self.lock:
            self.flag = value
            self.condition.notify_all()

    def begin(self) -> Optional[bool]:
        """
        Wait for the flag to be set, with a timeout.

        Args:
            timeout: Time to wait in seconds

        Returns:
            The flag value if the timeout hasn't expired, None if it has
        """
        while True:
            try:
                msg = self.in_queue.get(block=True, timeout=0.1)
                if msg is None:
                    break
                parsed_msg = json.loads(msg)
                payload = parsed_msg["msg"]
                timeout = float(parsed_msg["timeout"])
                self.current_messages[timeout] = payload
            except queue.Empty:
                # no new messages in the queue
                pass

            if len(self.current_messages) > 0:
                items = self.current_messages.items()
                to_del = []
                for k, v in items:
                    # Timeout occurred
                    if k < time.time():
                        print("TIMED OUT, SENDING MISS MSG")
                        print(v)
                        self.out_queue.put(json.dumps(v))
                        to_del.append(k)
                for k in to_del:
                    del self.current_messages[k]
