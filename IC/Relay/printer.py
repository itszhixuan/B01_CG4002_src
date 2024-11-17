from enum import Enum


class THREAD:
    FAIL = "\033[95m"
    RELAY_1 = "\033[94m"
    RELAY_2 = "\033[96m"
    AI = "\033[92m"
    PUB = "\033[93m"
    EVAL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def log(thread: THREAD, msg: str):
    print(thread + msg)
