from enum import Enum


class Action(Enum):
    BASKET = 0
    BOWL = 1
    LOGOUT = 2
    BOMB = 3
    RELOAD = 4
    SHIELD = 5
    SOCCER = 6
    VOLLEY = 7

    @staticmethod
    def from_int(value):
        for action in Action:
            if action.value == value:
                return action.name.lower()  # Return the string name of the enum
        return None  # Return None if the value does not match any enum
