
# Positive Rewards
from simulation.brain import CRITICAL_HUNGER, CRITICAL_THIRST, HUNGER_TO_START_FORAGING, HUNGER_TO_START_HUNTING
from simulation.goal_type import GoalType
from simulation.models import Critter, DietType


REWARD_EAT = 25.0
REWARD_DRINK = 25.0
REWARD_BREED = 100.0
REWARD_ENERGY_GAINED = 1.0

# Negative Rewards
PENALTY_LOST_HEALTH = -2.0
PENALTY_WASTED_GOAL = -1.0  # Pursuing a goal that does nothing
PENALTY_DEATH = -200.0

# Penalties for crossing critical thresholds
PENALTY_CROSSED_HUNGER_THRESHOLD = -10.0
PENALTY_CROSSED_THIRST_THRESHOLD = -10.0


def get_reward_for_goal(before: Critter, after: Critter, goal: GoalType,
                        action_successful: bool, died: bool) -> float:
    """
    Calculates the net reward based on the change in a critter's state and the
    goal is was pursuing.
    """
    if died:
        return PENALTY_DEATH

    reward = 0.0

    # --- Penalize crossing into a critical state ---
    if after.hunger > CRITICAL_HUNGER and before.hunger <= CRITICAL_HUNGER:
        reward += PENALTY_CROSSED_HUNGER_THRESHOLD

    if after.thirst > CRITICAL_THIRST and before.thirst <= CRITICAL_THIRST:
        reward += PENALTY_CROSSED_THIRST_THRESHOLD

    # --- Reward positive changes in state ---
    if after.hunger < before.hunger:
        reward += REWARD_EAT

    if after.thirst < before.thirst:
        reward += REWARD_DRINK

    if after.energy > before.energy:
        reward += (after.energy - before.energy) * REWARD_ENERGY_GAINED

    # --- Penalize negative changes in state ---
    if after.health < before.health:
        reward += (before.health - after.health) * PENALTY_LOST_HEALTH

    # --- Handle specific goal outcomes ---
    if goal == GoalType.BREED and action_successful:
        reward += REWARD_BREED

    # Penalize pursuing a goal that had no effect
    if not action_successful:
        reward += PENALTY_WASTED_GOAL

    return reward
