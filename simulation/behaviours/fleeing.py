from simulation.brain import SENSE_RADIUS, ActionType
from simulation.models import DietType


class FleeingBehavior:
    def get_action(self, critter, all_critters):
        """
        Scans for nearby predators. If one is found, returns a FLEE action.
        Otherwise, returns None.
        """
        nearby_carnivores = [
            other
            for other in all_critters
            if other.diet == DietType.CARNIVORE
            and abs(other.x - critter.x) <= SENSE_RADIUS
            and abs(other.y - critter.y) <= SENSE_RADIUS
        ]

        if nearby_carnivores:
            closest_predator = min(
                nearby_carnivores,
                key=lambda c: abs(c.x - critter.x) + abs(c.y - critter.y),
            )
            # If a predator is found, the action is to FLEE.
            return {
                "type": ActionType.FLEE,
                "dx": critter.x - closest_predator.x,
                "dy": critter.y - closest_predator.y,
                "predator": closest_predator,
            }

        # If no predators are nearby, return None.
        return None
