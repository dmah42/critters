from simulation.models import AIState
from simulation.action_type import ActionType

ENERGY_TO_START_RESTING = 30.0
ENERGY_TO_STOP_RESTING = 90.0

HEALTH_TO_BREED = 90.0
MAX_HUNGER_TO_BREED = 15.0
MAX_THIRST_TO_BREED = 15.0

CRITICAL_THIRST = 75.0
THIRST_TO_START_DRINKING = 40.0
THIRST_TO_STOP_DRINKING = 20.0

CRITICAL_HUNGER = 80.0
HUNGER_TO_START_FORAGING = 50.0
HUNGER_TO_STOP_FORAGING = 25.0

SENSE_RADIUS = 5


class CritterAI:
    def __init__(self, critter, world, all_critters, modules):
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

    def determine_action(self):
        """
        Determines the single best action using a two-phase process:
        1. determine the primary GOAL
        2. plan the best ACTION
        """

        goal = self._get_primary_goal()

        if goal == ActionType.FLEE:
            return self.fleeing_module.get_action(self.critter, self.all_critters)

        if goal == ActionType.REST:
            return {"type": ActionType.REST}

        if goal == ActionType.DRINK:
            # If we can drink or see water, do it. otherwise walk to find it.
            action = self.water_seeking_module.get_action(self.critter, self.world)
            return (
                action
                if action
                else self.moving_module.get_action(self.critter, self.all_critters)
            )

        if goal == ActionType.EAT:
            # If we can eat or see food, do it. otherwise walk to find it.
            action = self.foraging_module.get_action(
                self.critter, self.world, self.all_critters
            )
            return (
                action
                if action
                else self.moving_module.get_action(self.critter, self.all_critters)
            )

        if goal == ActionType.BREED:
            # If we can breed or see a mate, do it. otherwise just wander.
            action = self.mate_seeking_module.get_action(
                self.critter, self.all_critters
            )
            return (
                action
                if action
                else self.moving_module.get_action(self.critter, self.all_critters)
            )

        # Default: wander
        return self.moving_module.get_action(self.critter, self.all_critters)

    def _get_primary_goal(self):
        """
        Runs through a strict priority list to determine the single
        most important goal for the critter on this tick
        """
        critter = self.critter

        is_tired = critter.energy < ENERGY_TO_START_RESTING
        is_thirsty = critter.thirst >= THIRST_TO_START_DRINKING
        is_hungry = critter.hunger >= HUNGER_TO_START_FORAGING
        is_horny = (
            critter.health >= HEALTH_TO_BREED
            and critter.hunger < MAX_HUNGER_TO_BREED
            and critter.thirst < MAX_THIRST_TO_BREED
            and critter.breeding_cooldown == 0
        )

        # --- priority 1: flee ---
        # TODO: cache this so we don't call get_action twice.
        if self.fleeing_module and self.fleeing_module.get_action(
            critter, self.all_critters
        ):
            return ActionType.FLEE

        # --- priority 2: rest ---
        # If a critter is critically tired, it's only goal is to rest.
        # This overrides all other needs except for fleeing.
        if is_tired:
            return ActionType.REST

        # --- priority 3: other critical needs ---
        if critter.thirst > CRITICAL_THIRST:
            return ActionType.DRINK
        if critter.hunger > CRITICAL_HUNGER:
            return ActionType.EAT

        # --- priority 3: hysteresis ---
        # Rest comes before anything else.
        if (
            critter.ai_state == AIState.RESTING
            and critter.energy < ENERGY_TO_STOP_RESTING
        ):
            return ActionType.REST
        if (
            critter.ai_state in [AIState.DRINKING, AIState.SEEKING_WATER]
            and critter.thirst > THIRST_TO_STOP_DRINKING
        ):
            return ActionType.DRINK
        if (
            critter.ai_state in [AIState.EATING, AIState.SEEKING_FOOD]
            and critter.hunger > HUNGER_TO_STOP_FORAGING
        ):
            return ActionType.EAT

        # --- priority 4: new goal ---
        if is_thirsty:
            return ActionType.DRINK
        if is_hungry:
            return ActionType.EAT
        if is_tired:
            return ActionType.REST
        if is_horny:
            return ActionType.BREED

        return ActionType.WANDER
