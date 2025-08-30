from typing import Any, Dict, List, Optional, Tuple
from simulation.behaviours.behavior import AIAction, Behavior
from simulation.behaviours.wandering import WanderingBehavior
from simulation.goal_type import GoalType
from simulation.action_type import ActionType
from simulation.mapping import STATE_TO_GOAL_MAP
from simulation.models import Critter, DietType
from simulation.world import World

CRITICAL_ENERGY = 5.0
ENERGY_TO_START_RESTING = 50.0
MAX_ENERGY = 100.0

HERBIVORE_MIN_ENERGY_TO_BREED = 50.0
CARNIVORE_MIN_ENERGY_TO_BREED = 20.0

MIN_HEALTH_TO_BREED = 90.0
MAX_HUNGER_TO_BREED = 30.0
MAX_THIRST_TO_BREED = 25.0

MAX_THIRST = 100.0
CRITICAL_THIRST = 75.0
THIRST_TO_START_DRINKING = 0.75 * CRITICAL_THIRST

MAX_HUNGER = 100.0
CRITICAL_HUNGER = 80.0
HUNGER_TO_START_FORAGING = 0.75 * CRITICAL_HUNGER
HUNGER_TO_START_HUNTING = 0.3 * CRITICAL_HUNGER
HUNGER_TO_START_AMBUSHING = 0.2 * CRITICAL_HUNGER

SENSE_RADIUS = 5


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
        self.breeding_module = modules.get("breeding")
        self.wandering_module = WanderingBehavior()

    def determine_action(self) -> Tuple[GoalType, AIAction]:
        """
        Determines the primary goal and single best action to achieve it.
        1. determine the primary GOAL
        2. plan the best ACTION
        Returns a tuple containing both.
        """
        goal: GoalType = self._get_primary_goal()
        action: AIAction = self.get_action_for_goal(goal)
        return (goal, action)

    def get_action_for_goal(self, goal: GoalType) -> AIAction:
        """
        Takes a pre-determined goal and finds the best action to achieve it
        using the available behavior modules.
        """
        # Default behaviour will be to wander.
        action = None

        if goal == GoalType.SURVIVE_DANGER and self.fleeing_module:
            action = self.fleeing_module.get_action(
                self.critter, self.world, self.all_critters)
        elif goal == GoalType.RECOVER_ENERGY:
            action = AIAction(type=ActionType.REST)
        elif goal == GoalType.QUENCH_THIRST:
            action = self.water_seeking_module.get_action(
                self.critter, self.world, self.all_critters)
            if not action:
                action = self.foraging_module.get_action(
                    self.critter, self.world, self.all_critters)
        elif goal == GoalType.SATE_HUNGER:
            action = self.foraging_module.get_action(
                self.critter, self.world, self.all_critters)
        elif goal == GoalType.BREED:
            action = self.breeding_module.get_action(
                self.critter, self.world, self.all_critters)
        elif goal == GoalType.SEEK_MATE:
            action = self.mate_seeking_module.get_action(
                self.critter, self.world, self.all_critters)
        elif goal == GoalType.IDLE:
            action = self.moving_module.get_action(
                self.critter, self.world, self.all_critters)

        if not action:
            action: AIAction = self.wandering_module.get_action(
                self.critter, self.world, self.all_critters)

        return action

    def _get_primary_goal(self) -> GoalType:
        """
        Calculates a "need score" for all possible goals and returns the one
        with the highest score.
        """
        critter = self.critter

        # Fleeing is the top priority.
        # TODO: cache this so we don't call get_action twice.
        if self.fleeing_module and self.fleeing_module.get_action(
            critter, self.world, self.all_critters
        ):
            return GoalType.SURVIVE_DANGER

        # Critical needs come first
        if critter.energy <= CRITICAL_ENERGY:
            return GoalType.RECOVER_ENERGY

        if critter.thirst > CRITICAL_THIRST:
            return GoalType.QUENCH_THIRST

        if critter.hunger > CRITICAL_HUNGER:
            return GoalType.SATE_HUNGER

        # Opportunities to reproduce should be taken
        if self.breeding_module:
            if (
                critter.health >= MIN_HEALTH_TO_BREED
                and critter.hunger < MAX_HUNGER_TO_BREED
                and critter.thirst < MAX_THIRST_TO_BREED
                and critter.energy >= (CARNIVORE_MIN_ENERGY_TO_BREED if critter.diet == DietType.CARNIVORE else HERBIVORE_MIN_ENERGY_TO_BREED)
                and critter.breeding_cooldown == 0
            ):

                if self.breeding_module.get_action(
                    critter, self.world, self.all_critters
                ):
                    return GoalType.BREED

        # Calculate scores for any internal needs
        scores = {
            GoalType.RECOVER_ENERGY: 0,
            GoalType.QUENCH_THIRST: 0,
            GoalType.SATE_HUNGER: 0,
            GoalType.SEEK_MATE: 0,
            GoalType.IDLE: 0.1,  # small base score to be the default
        }

        if critter.energy < ENERGY_TO_START_RESTING:
            scores[GoalType.RECOVER_ENERGY] = (MAX_ENERGY - critter.energy) / (
                MAX_ENERGY - ENERGY_TO_START_RESTING
            )

        if critter.thirst >= THIRST_TO_START_DRINKING:
            scores[GoalType.QUENCH_THIRST] = critter.thirst / \
                THIRST_TO_START_DRINKING

        if critter.diet == DietType.HERBIVORE:
            if critter.hunger >= HUNGER_TO_START_FORAGING:
                scores[GoalType.SATE_HUNGER] = critter.hunger / \
                    HUNGER_TO_START_FORAGING
        elif critter.diet == DietType.CARNIVORE:
            if critter.hunger >= HUNGER_TO_START_HUNTING:
                scores[GoalType.SATE_HUNGER] = critter.hunger / \
                    HUNGER_TO_START_HUNTING
        else:
            raise NotImplementedError(f"Unknown diet type {critter.diet.name}")

        is_horny = (
            critter.energy >= (CARNIVORE_MIN_ENERGY_TO_BREED if critter.diet ==
                               DietType.CARNIVORE else HERBIVORE_MIN_ENERGY_TO_BREED)
            and critter.health >= MIN_HEALTH_TO_BREED
            and critter.hunger < MAX_HUNGER_TO_BREED
            and critter.thirst < MAX_THIRST_TO_BREED
            and critter.breeding_cooldown == 0
        )
        if is_horny:
            scores[GoalType.SEEK_MATE] = 1.0

        # Apply the commitment bonus
        committed_goal = STATE_TO_GOAL_MAP.get(critter.ai_state)
        if committed_goal and committed_goal in scores and scores[committed_goal] > 0:
            scores[committed_goal] *= critter.commitment

        return max(scores, key=scores.get)
