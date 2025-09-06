from typing import Any, Dict, List, Optional
from simulation.behaviours.behavior import AIAction
from simulation.behaviours.foraging import ForagingBehavior
from simulation.brain import (
    ENERGY_TO_START_RESTING,
    HUNGER_TO_START_AMBUSHING,
    HUNGER_TO_START_HUNTING,
    THIRST_TO_START_DRINKING,
    MAX_ENERGY,
    ActionType,
)
from simulation.models import AIState, Critter, DietType
from simulation.pathfinding import find_path
from simulation.world import World

# A multiplier that affects how far a carnivore is willing to chase based on its energy.
# A higher value makes them more willing to attempt long-distance hunts.
HUNTING_WILLINGNESS_FACTOR = 1.2

# These weights control the carnivore's hunting priorities.
HEALTH_VULNERABILITY_WEIGHT = 1.5  # How much to prioritize low health
ENERGY_VULNERABILITY_WEIGHT = 1.0  # How much to prioritize low energy
# A bonus for distracted (eating/drinking) prey
DISTRACTION_VULNERABILITY_BONUS = 0.5


class HuntingBehavior(ForagingBehavior):
    def _find_best_target(self, critter: Critter, potential_prey: List[Critter]) -> Optional[Critter]:
        """
        Calculates a vulnerability score for each potential prey and returns
        the one with the highest score.
        """
        best_target = None
        max_vulnerability_score = -1

        for prey in potential_prey:
            health_score = (prey.max_health / (prey.health + 1)
                            ) * HEALTH_VULNERABILITY_WEIGHT
            energy_score = (MAX_ENERGY / (prey.energy + 1)) * \
                ENERGY_VULNERABILITY_WEIGHT

            distraction_bonus = 0
            if prey.ai_state in [AIState.EATING, AIState.DRINKING]:
                distraction_bonus = DISTRACTION_VULNERABILITY_BONUS

            distance = abs(prey.x - critter.x) + abs(prey.y - critter.y)
            distance_penalty = distance / critter.perception

            total_score = (health_score + energy_score +
                           distraction_bonus) - distance_penalty

            if total_score > max_vulnerability_score:
                max_vulnerability_score = total_score
                best_target = prey

        return best_target

    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Optional[AIAction]:
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
            return AIAction(type=ActionType.ATTACK, target_critter=adjacent_prey[0])

        if critter.hunger >= HUNGER_TO_START_HUNTING:
            # 2. If no adjacent prey, scan the wider area to find a target to hunt.
            nearby_herbivores = [
                prey
                for prey in potential_prey
                if abs(prey.x - critter.x) <= critter.perception
                and abs(prey.y - critter.y) <= critter.perception
            ]

            if nearby_herbivores:
                best_target = self._find_best_target(
                    critter, nearby_herbivores)

                if best_target:
                    # Cost/benefit analysis
                    energy_ratio = critter.energy / MAX_ENERGY
                    max_chase_distance = critter.perception * \
                        energy_ratio * HUNTING_WILLINGNESS_FACTOR

                    distance_to_target = abs(
                        best_target.x - critter.x) + abs(best_target.y - critter.y)

                    # Only commit to the chase if the target is within the willingness distance.
                    if distance_to_target <= max_chase_distance:
                        end_pos = (best_target.x, best_target.y)
                        # If prey is found, and we can find a path to it, MOVE to it.
                        path = find_path(
                            world, (critter.x, critter.y), end_pos)

                        if path and len(path) > 1:
                            next_step = path[1]

                            return AIAction(
                                type=ActionType.MOVE,
                                dx=next_step[0] - critter.x,
                                dy=next_step[1] - critter.y,
                                target=end_pos,
                            )

        if critter.hunger >= HUNGER_TO_START_AMBUSHING:
            # 3. If no adjacent prey, and only moderately hungry, see if there's
            # an opportunity. Ensure we don't lie in wait if we're thirsty or tired.
            if critter.thirst >= THIRST_TO_START_DRINKING or critter.energy < ENERGY_TO_START_RESTING:
                return None

            ambush_radius = max(2, int(critter.perception / 2))
            nearby_herbivores = [
                prey
                for prey in potential_prey
                if abs(prey.x - critter.x) <= ambush_radius
                and abs(prey.y - critter.y) <= ambush_radius
            ]

            if nearby_herbivores:
                best_target = self._find_best_target(
                    critter, nearby_herbivores)

                if best_target:
                  # If prey is found, and we can find a path to it, MOVE to it.
                  end_pos = (best_target.x, best_target.y)
                  path = find_path(world, (critter.x, critter.y), end_pos)

                  if path and len(path) > 1:
                      next_step = path[1]

                      return AIAction(
                          type=ActionType.MOVE,
                          dx=next_step[0] - critter.x,
                          dy=next_step[1] - critter.y,
                          target=end_pos,
                      )
            else:
                # No prey in the ambush zone.  Time to wait...
                return AIAction(type=ActionType.AMBUSH)

        # 3. If no action can be taken, return None.
        return None
