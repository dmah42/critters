from simulation.models import AIState
from simulation.terrain_type import TerrainType
from simulation.action_type import ActionType

ENERGY_TO_START_RESTING = 30.0
ENERGY_TO_STOP_RESTING = 90.0

HEALTH_TO_BREED = 90.0
MAX_HUNGER_TO_BREED = 15.0
MAX_THIRST_TO_BREED = 15.0

THIRST_TO_START_DRINKING = 20.0
THIRST_TO_STOP_DRINKING = 5.0

HUNGER_TO_START_FORAGING = 25.0
HUNGER_TO_STOP_FORAGING = 16.0

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

    def determine_action(self):
        """
        Goes through a priority list to determine the single best action for this tick.
        Returns a dictionary representing the action, e.g., {'type': 'REST'}.
        """
        critter = self.critter  # for convenience

        # --- High-Level State Checks ---
        is_tired = critter.energy < ENERGY_TO_START_RESTING
        is_thirsty = critter.thirst >= THIRST_TO_START_DRINKING
        is_hungry = critter.hunger >= HUNGER_TO_START_FORAGING
        ready_to_breed = (
            critter.health >= HEALTH_TO_BREED
            and critter.hunger < MAX_HUNGER_TO_BREED
            and critter.thirst < MAX_THIRST_TO_BREED
            and critter.breeding_cooldown == 0
        )

        # --- Priority 1: FLEE (if the module exists) ---
        if self.fleeing_module:
            action = self.fleeing_module.get_action(critter, self.all_critters)
            if action:
                return action

        # --- Priority 2: REST and keep resting if we've started
        if is_tired or (
            critter.ai_state == AIState.RESTING
            and critter.energy < ENERGY_TO_STOP_RESTING
        ):
            return {"type": ActionType.REST}

        # --- Priority 3: DRINK or SEEK_WATER ---
        if self.water_seeking_module:
            if is_thirsty or (
                critter.ai_state == AIState.THIRSTY
                and critter.thirst > THIRST_TO_STOP_DRINKING
            ):
                action = self.water_seeking_module.get_action(critter, self.world)
                if action:
                    return action

        # --- Priority 4: EAT/ATTACK or SEEK_FOOD ---
        if self.foraging_module:
            if is_hungry or (
                critter.ai_state == AIState.HUNGRY
                and critter.hunger > HUNGER_TO_STOP_FORAGING
            ):
                action = self.foraging_module.get_action(
                    critter, self.world, self.all_critters
                )
                if action:
                    return action

        # --- Priority 5: BREED or SEEK_MATE ---
        if ready_to_breed and self.mate_seeking_module:
            action = self.mate_seeking_module.get_action(critter, self.all_critters)
            if action:
                return action

        # --- Final Priority: WANDER ---
        # If all else fails, wander randomly.
        return {"type": ActionType.WANDER}
