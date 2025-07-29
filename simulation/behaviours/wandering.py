import random
from simulation.action_type import ActionType
from simulation.behaviours.moving import MovingBehavior

DIRECTION_CHANGE_PROBABILITY = 0.1

# prettier-ignore
POSSIBLE_DIRECTIONS = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
]


class WanderingBehavior(MovingBehavior):
    def get_action(self, critter, _):
        """
        Determines a direction in which to wander, biasing towards
        the critter's last known velocity.
        """
        if (
            critter.vx != 0 or critter.vy != 0
        ) and random.random() > DIRECTION_CHANGE_PROBABILITY:
            dx, dy = critter.vx, critter.vy
        else:
            dx, dy = random.choice(POSSIBLE_DIRECTIONS)

        return {"type": ActionType.MOVE, "dx": dx, "dy": dy}
