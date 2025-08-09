from typing import Any, Dict, List
from simulation.behaviours.foraging import ForagingBehavior
from simulation.brain import ActionType
from simulation.models import Critter, DietType
from simulation.pathfinding import find_path
from simulation.world import World


class HuntingBehavior(ForagingBehavior):
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Dict[str, Any]:
        """
        Determines the complete foraging action for a carnivore.
        Checks for adjacent prey first (ATTACK), then scans for distant
        prey to hunt (SEEK_FOOD).
        Returns a complete action dictionary, or None.
        """
        potential_prey = [
            other
            for other in all_critters
            if other.diet == DietType.HERBIVORE and not other.is_ghost
        ]

        # 1. First, check for adjacent prey to ATTACK.
        adjacent_prey = [
            prey
            for prey in potential_prey
            if abs(prey.x - critter.x) <= 1 and abs(prey.y - critter.y) <= 1
        ]
        if adjacent_prey:
            # If prey is adjacent, the action is to ATTACK.
            return {"type": ActionType.ATTACK, "target": adjacent_prey[0]}

        # 2. If no adjacent prey, scan the wider area to find a target to hunt.
        nearby_herbivores = [
            prey
            for prey in potential_prey
            if abs(prey.x - critter.x) <= critter.perception
            and abs(prey.y - critter.y) <= critter.perception
        ]

        if nearby_herbivores:
            # Sort by weakest first then closest to break ties
            nearby_herbivores.sort(
                key=lambda prey: (
                    prey.health,
                    abs(prey.x - critter.x) + abs(prey.y + critter.y),
                )
            )
            best_target = nearby_herbivores[0]

            # If prey is found, and we can find a path to it, MOVE to it.
            end_pos = (best_target.x, best_target.y)
            path = find_path(world, (critter.x, critter.y), end_pos)

            if path and len(path) > 1:
                next_step = path[1]

                return {
                    "type": ActionType.MOVE,
                    "dx": next_step[0] - critter.x,
                    "dy": next_step[1] - critter.y,
                    "target": end_pos,
                }

        # 3. If no action can be taken, return None.
        return None
