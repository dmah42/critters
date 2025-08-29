from typing import List, Optional

from simulation.action_type import ActionType
from simulation.behaviours.behavior import AIAction, Behavior
from simulation.brain import (
    CARNIVORE_MIN_ENERGY_TO_BREED,
    HERBIVORE_MIN_ENERGY_TO_BREED,
    MAX_HUNGER_TO_BREED,
    MAX_THIRST_TO_BREED,
    MIN_HEALTH_TO_BREED,
)
from simulation.models import Critter, DietType
from simulation.pathfinding import find_path
from simulation.world import World

COURTSHIP_RADIUS = 2


class BreedingBehavior(Behavior):
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Optional[AIAction]:
        """
        Checks for a high-priority, short-range breeding opportunity.
        Returns a BREED or MOVE action if an opportunity exists, otherwise None.
        """
        potential_mates = [
            other
            for other in all_critters
            if other.id != critter.id
            and other.diet == critter.diet
            and abs(other.x - critter.x) <= COURTSHIP_RADIUS
            and abs(other.y - critter.y) <= COURTSHIP_RADIUS
            and other.energy >= (CARNIVORE_MIN_ENERGY_TO_BREED if other.diet == DietType.CARNIVORE else HERBIVORE_MIN_ENERGY_TO_BREED)
            and other.health >= MIN_HEALTH_TO_BREED
            and other.hunger < MAX_HUNGER_TO_BREED
            and other.thirst < MAX_THIRST_TO_BREED
            and other.breeding_cooldown == 0
        ]

        if not potential_mates:
            return None

        # Find the closest of these potential mates
        closest_mate = min(
            potential_mates,
            key=lambda c: abs(c.x - critter.x) + abs(c.y - critter.y),
        )

        # If the closest mate is adjacent, the action is to BREED
        if (
            abs(closest_mate.x - critter.x) <= 1
            and abs(closest_mate.y - critter.y) <= 1
        ):
            return AIAction(type=ActionType.BREED, target_critter=closest_mate)
        else:
            # If the mate is close but not adjacent, the action is to MOVE to them
            start_pos = (critter.x, critter.y)
            end_pos = (closest_mate.x, closest_mate.y)

            path = find_path(world, start_pos, end_pos)

            if path and len(path) > 1:
                next_step = path[1]

                return AIAction(
                    type=ActionType.MOVE,
                    dx=next_step[0] - critter.x,
                    dy=next_step[1] - critter.y,
                    target=end_pos,
                )
