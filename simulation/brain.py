from typing import Any, Dict, List
from simulation.behaviours.behavior import Behavior
from simulation.behaviours.wandering import WanderingBehavior
from simulation.goal_type import GoalType
from simulation.action_type import ActionType
from simulation.mapping import STATE_TO_GOAL_MAP
from simulation.models import Critter
from simulation.world import World

ENERGY_TO_START_RESTING = 30.0
ENERGY_TO_STOP_RESTING = 90.0
MAX_ENERGY = 100.0

HEALTH_TO_BREED = 90.0
MAX_HUNGER_TO_BREED = 15.0
MAX_THIRST_TO_BREED = 15.0

CRITICAL_THIRST = 75.0
THIRST_TO_START_DRINKING = 40.0
THIRST_TO_STOP_DRINKING = 20.0

CRITICAL_HUNGER = 80.0
HUNGER_TO_START_FORAGING = 50.0
HUNGER_TO_STOP_FORAGING = 25.0

CRITICAL_ENERGY = 5.0

SENSE_RADIUS = 5

# A bonus applied to the score of the current goal, making the AI more focused.
# A higher value means more focused, a lower value means more easily distracted.
# TODO: think about making this a critter trait.
COMMITMENT_BONUS = 1.25


class CritterAI:
    def __init__(
        self,
        critter: Critter,
        world: World,
        all_critters: List[Critter],
        modules: Dict[str, Behavior],
    ):
        """
        Initializes the AI brain with the critter it controls and its
        set of behavior modules.
        """
        self.critter = critter
        self.world = world
        self.all_critters = all_critters

        # Store the behavior modules
        self.fleeing_module = modules.get("fleeing")
        self.foraging_module = modules.get("foraging")
        self.water_seeking_module = modules.get("water_seeking")
        self.mate_seeking_module = modules.get("mate_seeking")
        self.moving_module = modules.get("moving")
        self.wandering_module = WanderingBehavior()

    def determine_action(self) -> Dict[str, Any]:
        """
        Determines the primary goal and single best action to achieve it.
        1. determine the primary GOAL
        2. plan the best ACTION
        Returns a dictionary containing both.
        """

        goal: GoalType = self._get_primary_goal()

        action: ActionType = None

        if goal == GoalType.SURVIVE_DANGER:
            action = self.fleeing_module.get_action(
                self.critter, self.world, self.all_critters
            )

        elif goal == GoalType.RECOVER_ENERGY:
            action = {"type": ActionType.REST}

        elif goal == GoalType.QUENCH_THIRST:
            # If we can drink or see water, do it. otherwise walk to find it.
            action = self.water_seeking_module.get_action(
                self.critter, self.world, self.all_critters
            )

        elif goal == GoalType.SATE_HUNGER:
            # If we can eat or see food, do it. otherwise walk to find it.
            action = self.foraging_module.get_action(
                self.critter, self.world, self.all_critters
            )

        elif goal == GoalType.REPRODUCE:
            # If we can breed or see a mate, do it. otherwise just wander.
            action = self.mate_seeking_module.get_action(
                self.critter, self.world, self.all_critters
            )

        elif goal == GoalType.WANDER:
            # Social wandering
            action = self.moving_module.get_action(
                self.critter, self.world, self.all_critters
            )

        # If a goal was chosen but the behaviour module found no specific action,
        # wander determinedly in hope.
        if action is None:
            action = self.wandering_module.get_action(
                self.critter, self.world, self.all_critters
            )

        return {"goal": goal, "action": action}

    def _get_primary_goal(self) -> GoalType:
        """
        Calculates a "need score" for all possible goals and returns the one
        with the highest score.
        """
        critter = self.critter

        scores = {
            GoalType.SURVIVE_DANGER: 0,
            GoalType.RECOVER_ENERGY: 0,
            GoalType.QUENCH_THIRST: 0,
            GoalType.SATE_HUNGER: 0,
            GoalType.REPRODUCE: 0,
            GoalType.WANDER: 0.1,  # small base score to be the default
        }

        # Fleeing is the top priority.
        # TODO: cache this so we don't call get_action twice.
        if self.fleeing_module and self.fleeing_module.get_action(
            critter, self.world, self.all_critters
        ):
            return GoalType.SURVIVE_DANGER

        # Calculate scores for internal needs

        # Exhaustion is to be avoided at all costs.
        if critter.energy <= CRITICAL_ENERGY:
            return GoalType.RECOVER_ENERGY

        scores[GoalType.RECOVER_ENERGY] = (MAX_ENERGY - critter.energy) / (
            MAX_ENERGY - ENERGY_TO_START_RESTING
        )
        scores[GoalType.QUENCH_THIRST] = critter.thirst / THIRST_TO_START_DRINKING
        scores[GoalType.SATE_HUNGER] = critter.hunger / HUNGER_TO_START_FORAGING

        is_horny = (
            critter.health >= HEALTH_TO_BREED
            and critter.hunger < MAX_HUNGER_TO_BREED
            and critter.thirst < MAX_THIRST_TO_BREED
            and critter.breeding_cooldown == 0
        )
        if is_horny:
            scores[GoalType.REPRODUCE] = 1.0

        # Apply the commitment bonus
        committed_goal = STATE_TO_GOAL_MAP.get(critter.ai_state)
        if committed_goal and committed_goal in scores and scores[committed_goal] > 0:
            scores[committed_goal] *= COMMITMENT_BONUS

        return max(scores, key=scores.get)
