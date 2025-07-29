import random
from simulation.action_type import ActionType
from simulation.behaviours.moving import MovingBehavior


class WanderingBehavior(MovingBehavior):
    def get_action(self, critter, all_critters):
        """
        Returns a WANDER action with a random direction.
        """
        return {
            "type": ActionType.WANDER,
            "dx": random.choice([-1, 0, 1]),
            "dy": random.choice([-1, 0, 1]),
        }
