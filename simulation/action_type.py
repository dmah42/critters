import enum


class ActionType(enum.Enum):
    REST = "rest"
    DRINK = "drink"
    EAT = "eat"
    FLEE = "flee"
    SEEK_WATER = "seek_water"
    SEEK_FOOD = "seek_food"
    SEEK_MATE = "seek_mate"
    BREED = "breed"
    WANDER = "wander"
    ATTACK = "attack"
