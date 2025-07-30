import random
from simulation import logger
from simulation.action_type import ActionType
from simulation.behaviours.moving import MovingBehavior
from simulation.terrain_type import TerrainType

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
    def get_action(self, critter, world, _):
        """
        Determines a direction in which to wander, biasing towards
        the critter's last known velocity.
        """
        valid_directions = []
        for dx, dy in POSSIBLE_DIRECTIONS:
            tile = world.get_tile(critter.x + dx, critter.y + dy)
            if tile["terrain"] != TerrainType.WATER:
                valid_directions.append((dx, dy))

        if not valid_directions:
            logger.warning(f"{critter.id} is trapped unable to move")
            return {"type": ActionType.MOVE, "dx": 0, "dy": 0}

        has_momentum = critter.vx != 0 or critter.vy != 0

        # Normalize the velocity vector to get its direction (e.g., (5.0, 0.0) -> (1, 0))
        momentum_direction_dx = 1 if critter.vx > 0 else -1 if critter.vx < 0 else 0
        momentum_direction_dy = 1 if critter.vy > 0 else -1 if critter.vy < 0 else 0
        momentum_direction = (momentum_direction_dx, momentum_direction_dy)

        momentum_is_valid = momentum_direction in valid_directions

        if (
            has_momentum
            and momentum_is_valid
            and random.random() > DIRECTION_CHANGE_PROBABILITY
        ):
            dx, dy = critter.vx, critter.vy
        else:
            chosen_direction = random.choice(valid_directions)
            dx, dy = chosen_direction

        return {"type": ActionType.MOVE, "dx": dx, "dy": dy}
