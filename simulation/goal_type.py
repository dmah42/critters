import enum


class GoalType(enum.Enum):
    """
    Represents the high-level, long-term goals or needs of a critter.
    This is the "why" behind an action.
    """

    SURVIVE_DANGER = "survive_danger"  # Fleeing
    RECOVER_ENERGY = "recover_energy"  # Resting
    QUENCH_THIRST = "quench_thirst"  # Drinking or seeking water
    SATE_HUNGER = "sate_hunger"  # Eating or hunting
    BREED = "breed"  # There's a viable mate nearby, reproduce
    SEEK_MATE = "seek_mate"  # All other needs met, try to find a mate
    WANDER = "wander"  # Default, idle behavior
