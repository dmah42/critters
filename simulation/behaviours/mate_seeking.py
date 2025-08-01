from typing import Any, Dict, List
from simulation.behaviours.behavior import Behavior
from simulation.brain import (
    MIN_HEALTH_TO_BREED,
    MAX_HUNGER_TO_BREED,
    MAX_THIRST_TO_BREED,
    SENSE_RADIUS,
    ActionType,
)
from simulation.models import Critter
from simulation.pathfinding import find_path
from simulation.world import World


class MateSeekingBehavior(Behavior):
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Dict[str, Any]:
        """
        Determines the complete breeding-related action for a critter.
        Checks for adjacent mates first (BREED), then scans for distant
        mates to pursue (SEEK_MATE).
        Returns a complete action dictionary, or None.
        """
        # First, find all suitable mates within sensing range
        potential_mates = [
            other
            for other in all_critters
            if other.id != critter.id
            and other.diet == critter.diet
            and abs(other.x - critter.x) <= SENSE_RADIUS
            and abs(other.y - critter.y) <= SENSE_RADIUS
            and other.health >= MIN_HEALTH_TO_BREED
            and other.hunger < MAX_HUNGER_TO_BREED
            and other.thirst < MAX_THIRST_TO_BREED
            and other.breeding_cooldown == 0
        ]

        if not potential_mates:
            return None  # No suitable mates found

        # 1. Check if any of the potential mates are adjacent.
        for mate in potential_mates:
            if abs(mate.x - critter.x) <= 1 and abs(mate.y - critter.y) <= 1:
                # If a mate is adjacent, the action is to BREED.
                return {"type": ActionType.BREED, "partner": mate}

        # 2. If no mate is adjacent, find the closest one to move towards.
        closest_mate = min(
            potential_mates,
            key=lambda c: abs(c.x - critter.x) + abs(c.y - critter.y),
        )

        start_pos = (critter.x, critter.y)
        end_pos = (closest_mate.x, closest_mate.y)
        path = find_path(world, start_pos, end_pos)

        if path and len(path) > 1:
            next_step = path[1]

            return {
                "type": ActionType.MOVE,
                "dx": next_step[0] - critter.x,
                "dy": next_step[1] - critter.y,
                "target": end_pos,
            }

        # If there's no path to the mate, just return None
        return None
