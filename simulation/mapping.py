from simulation.goal_type import GoalType
from simulation.models import AIState

# This is our single, authoritative source of truth.
GOAL_TO_STATE_MAP = {
    GoalType.RECOVER_ENERGY: AIState.RESTING,
    GoalType.SURVIVE_DANGER: AIState.FLEEING,
    GoalType.QUENCH_THIRST: AIState.SEEKING_WATER,
    GoalType.SATE_HUNGER: AIState.SEEKING_FOOD,
    GoalType.BREED: AIState.BREEDING,
    GoalType.SEEK_MATE: AIState.SEEKING_MATE,
    GoalType.IDLE: AIState.IDLE,
}

# We programmatically create the inverse map.
# This dictionary comprehension swaps the keys and values.
STATE_TO_GOAL_MAP = {state: goal for goal, state in GOAL_TO_STATE_MAP.items()}

# We also need to add the more specific states back into the reverse map,
# as they all map to the same general goal.
STATE_TO_GOAL_MAP[AIState.DRINKING] = GoalType.QUENCH_THIRST
STATE_TO_GOAL_MAP[AIState.EATING] = GoalType.SATE_HUNGER
