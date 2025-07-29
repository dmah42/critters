from simulation.behaviours.foraging import ForagingBehavior
from simulation.brain import SENSE_RADIUS, ActionType
from simulation.models import DietType


class HuntingBehavior(ForagingBehavior):
    def get_action(self, critter, world, all_critters):
        """
        Determines the complete foraging action for a carnivore.
        Checks for adjacent prey first (ATTACK), then scans for distant
        prey to hunt (SEEK_FOOD).
        Returns a complete action dictionary, or None.
        """
        # 1. First, check for adjacent prey to ATTACK.
        adjacent_prey = [
            other
            for other in all_critters
            if other.diet == DietType.HERBIVORE
            and abs(other.x - critter.x) <= 1
            and abs(other.y - critter.y) <= 1
        ]
        if adjacent_prey:
            # If prey is adjacent, the action is to ATTACK.
            return {"type": ActionType.ATTACK, "target": adjacent_prey[0]}

        # 2. If no adjacent prey, scan the wider area to find a target to hunt.
        nearby_herbivores = [
            other
            for other in all_critters
            if other.diet == DietType.HERBIVORE
            and abs(other.x - critter.x) <= SENSE_RADIUS
            and abs(other.y - critter.y) <= SENSE_RADIUS
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

            # If prey is found, the action is to SEEK_FOOD (hunt).
            return {
                "type": ActionType.SEEK_FOOD,
                "dx": best_target.x - critter.x,
                "dy": best_target.y - critter.y,
                "target": (best_target.x, best_target.y),
            }

        # 3. If no action can be taken, return None.
        return None
