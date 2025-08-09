import enum


class ActionType(enum.Enum):
    """
    Represents the specific, concrete action a critter will execute on this tick.
    This is the "how" of the AI's decision.
    """

    REST = "rest"  # Stay still and recover energy
    DRINK = "drink"  # Consume water from an adjacent tile
    EAT = "eat"  # Consume food from the current tile
    ATTACK = "attack"  # Attack an adjacent critter
    AMBUSH = "ambush"  # Ambush a critter
    BREED = "breed"  # Reproduce with an adjacent mate
    MOVE = "move"  # Move towards a target destination
    IDLE = "idle"  # Do nothing (e.g., a fully satisfied critter)
