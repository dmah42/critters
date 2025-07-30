import json
import logging
import math
import random
from simulation.goal_type import GoalType
from simulation.mapping import GOAL_TO_STATE_MAP
from simulation.terrain_type import TerrainType
from simulation.brain import CRITICAL_HUNGER, CRITICAL_THIRST, MAX_ENERGY, ActionType
from simulation.models import (
    AIState,
    CauseOfDeath,
    Critter,
    DeadCritter,
    DietType,
    SimulationStats,
    TileState,
)
from simulation.factory import create_ai_for_critter
from simulation.world import DEFAULT_GRASS_FOOD

# Terrain constants
GRASS_REGROWTH_RATE = 0.1

# Critter constants
HUNGER_PER_TICK = 0.2
THIRST_PER_TICK = 0.25
BASE_ENERGY_COST_PER_MOVE = 0.1
UPHILL_ENERGY_MULTIPLIER = 1.1
DOWNHILL_ENERGY_MULTIPLIER = 0.8

# AI constants
HUNGER_RESTORED_PER_EAT = 10.0
EAT_AMOUNT = 5.0

ENERGY_REGEN_PER_TICK = 5.0

DRINK_AMOUNT = 25.0

HEALTH_DAMAGE_PER_TICK = 0.1

DAMAGE_PER_SIZE_POINT = 5.0

## Breeding constants
BREEDING_ENERGY_COST = 40.0
BREEDING_COOLDOWN_TICKS = 500
MUTATION_CHANCE = 0.1
MUTATION_AMOUNT = 0.2

logger = logging.getLogger(__name__)


def run_simulation_tick(world, session):
    """Process one tick of the world simulation. Called periodically."""
    print(".", end="")
    logger.info("+++ Starting tick +++")
    _process_tile_regrowth(session)
    _process_critter_ai(world, session)
    _record_statistics(session)
    logger.info("+++ Ending tick +++")
    print("|", end="", flush=True)


def _process_tile_regrowth(session):
    """
    Finds all depleted grass tiles and handles regrowth.
    If a tile regrows completely, remove the record.
    """
    depleted_tiles = (
        session.query(TileState)
        .filter(TileState.food_available < DEFAULT_GRASS_FOOD)
        .all()
    )

    tiles_to_delete = []

    for tile in depleted_tiles:
        tile.food_available += GRASS_REGROWTH_RATE

        if tile.food_available >= DEFAULT_GRASS_FOOD:
            tiles_to_delete.append(tile)

    for tile in tiles_to_delete:
        session.delete(tile)

    logger.info(
        f"Processed regrowth for {len(depleted_tiles)} tiles.  Deleted {len(tiles_to_delete)} tiles"
    )


def _process_critter_ai(world, session):
    """Handles the state changes and actions for living critters"""
    all_critters = session.query(Critter).all()

    if not all_critters:
        logger.warning("No living critters found.")
        return

    # Start tracking any critters that die this tick.
    deaths_this_tick = set()

    for critter in all_critters:
        # Check if we have a ghost in the machine
        if critter.id in deaths_this_tick:
            logger.info(f"Skipping update for ghost {critter.id}")
            continue
        _run_critter_logic(critter, world, session, all_critters, deaths_this_tick)

    logger.info(f"Processed AI for {len(all_critters)} critters.")


def _run_critter_logic(critter, world, session, all_critters, deaths_this_tick):
    """
    The main AI dispatcher for a single critter's turn.
    It creates the appropriate AI brain, gets an action, and executes it.
    """
    # --- Part 1: Universal State Updates (Health, Hunger, Death, etc.) ---
    # This initial block of code is the same as before.
    logger.info(f"  Processing critter {critter.id} [{critter.ai_state.name}]")
    critter.age += 1
    critter.hunger += HUNGER_PER_TICK
    critter.thirst += THIRST_PER_TICK
    if critter.breeding_cooldown > 0:
        critter.breeding_cooldown -= 1

    if critter.hunger > CRITICAL_HUNGER or critter.thirst > CRITICAL_THIRST:
        critter.health -= HEALTH_DAMAGE_PER_TICK

    if critter.health <= 0:
        cause = (
            CauseOfDeath.STARVATION
            if critter.hunger > critter.thirst
            else CauseOfDeath.THIRST
        )
        _handle_death(critter, cause, session, deaths_this_tick)
        return

    # --- Part 2: Get Action from the AI Brain ---
    # All complex decision-making is now handled by these two lines.
    brain = create_ai_for_critter(critter, world, all_critters)
    result = brain.determine_action()
    goal = result["goal"]
    action = result["action"]

    if not action:
        raise RuntimeError(
            f"CRITICAL BUG: CritterAI for {critter.id} returned a None action.\n"
            f"  Critter: {critter.to_dict()}"
        )

    action_type = action["type"]

    # Map to an AI state for commitments to goals.
    critter.ai_state = GOAL_TO_STATE_MAP[goal]
    if action_type == ActionType.EAT:
        critter.ai_state = AIState.EATING
    elif action_type == ActionType.DRINK:
        critter.ai_state = AIState.DRINKING
    elif action_type == ActionType.BREED:
        critter.ai_state = AIState.BREEDING

    # --- Part 3: Execute the action ---

    # This is a simple "switch" statement that executes the brain's decision.
    if action_type == ActionType.REST:
        critter.energy += ENERGY_REGEN_PER_TICK
        critter.energy = min(critter.energy, MAX_ENERGY)
        logger.info(f"    rested: energy: {critter.energy:.2f}")

    elif action_type == ActionType.DRINK:
        critter.thirst -= DRINK_AMOUNT
        critter.thirst = max(critter.thirst, 0)
        logger.info(f"    drank: thirst: {critter.thirst}")

    elif action_type == ActionType.EAT:
        current_tile = world.get_tile(critter.x, critter.y)
        amount_to_eat = min(current_tile["food_available"], EAT_AMOUNT)
        new_tile_food = current_tile["food_available"] - amount_to_eat
        _update_tile_food(session, critter.x, critter.y, new_tile_food)
        critter.hunger -= (amount_to_eat / EAT_AMOUNT) * HUNGER_RESTORED_PER_EAT
        critter.hunger = max(critter.hunger, 0)
        logger.info(f"    ate {amount_to_eat}: hunger: {critter.hunger:.2f}")

    elif action_type == ActionType.ATTACK:
        prey = action["target"]
        damage = critter.size * DAMAGE_PER_SIZE_POINT

        prey.health -= damage

        logger.info(f"    attacking: {prey.id} for {damage:.2f}")

        if prey.health <= 0:
            _handle_death(prey, CauseOfDeath.PREDATION, session, deaths_this_tick)
            critter.hunger = 0
        else:
            logger.info(f"      {prey.id} survived with {prey.health:.2f} health")

    elif action_type == ActionType.BREED:
        mate = action["partner"]
        logger.info(f"    breeding: {mate.id}")
        _reproduce(critter, mate, session)

    elif action_type == ActionType.MOVE:
        if goal == GoalType.SURVIVE_DANGER:
            predator = action["predator"]
            logger.info(f"    fleeing from {predator.id}")

        target = action.get("target")  # Get the specific target tile if it exists
        _execute_move(
            critter,
            world,
            action["dx"],
            action["dy"],
            target=target,
        )

    else:
        raise NotImplementedError(f"Unimplemented action '{action_type.name}'")


def _update_tile_food(session, x, y, new_food_value):
    """
    Updates the food value for a specific tile and saves it to the session.
    """
    tile = session.query(TileState).get((x, y))
    if tile:
        tile.food_available = new_food_value
    else:
        tile = TileState(x=x, y=y, food_available=new_food_value)
        session.add(tile)


def _execute_move(critter, world, dx, dy, target=None):
    """
    Executes a move for a critter, checking for obstacles and goals.
    (This is a new helper function to hold the movement loop)
    """
    old_x, old_y = critter.x, critter.y

    # Normalize the direction vector to get single steps
    move_dx = 1 if dx > 0 else -1 if dx < 0 else 0
    move_dy = 1 if dy > 0 else -1 if dy < 0 else 0

    if move_dx == 0 and move_dy == 0:
        critter.vx, critter.vy = 0, 0
        return

    critter.movement_progress += critter.speed
    steps_to_take = int(critter.movement_progress)
    critter.movement_progress -= steps_to_take

    hit_obstacle = False

    for _ in range(steps_to_take):
        new_x, new_y = critter.x + move_dx, critter.y + move_dy
        destination_tile = world.get_tile(new_x, new_y)

        if destination_tile["terrain"] == TerrainType.WATER:
            logger.info("    unable to move. water")
            hit_obstacle = True
            break

        current_tile = world.get_tile(critter.x, critter.y)

        height_diff = destination_tile["height"] - current_tile["height"]
        energy_cost = BASE_ENERGY_COST_PER_MOVE
        if height_diff > 0:
            energy_cost += height_diff * UPHILL_ENERGY_MULTIPLIER
        elif height_diff < 0:
            energy_cost += height_diff * DOWNHILL_ENERGY_MULTIPLIER

        if critter.energy < energy_cost:
            logger.info("    unable to move. not enough energy")
            hit_obstacle = True
            break

        critter.energy -= energy_cost

        critter.x = new_x
        critter.y = new_y

        # Check if the goal of the move was met
        if target and critter.x == target[0] and critter.y == target[1]:
            break

    if hit_obstacle:
        # Force a reset of the direction of travel
        critter.vx, critter.vy = 0, 0
    else:
        critter.vx, critter.vy = critter.x - old_x, critter.y - old_y


def _handle_death(critter, cause, session, deaths_this_tick):
    """Handles the death of a critter"""

    # Check that they are not already marked for death
    if critter.id in deaths_this_tick:
        raise RuntimeError(
            f"--- !!! WARNING: DUPLICATE DEATH ATTEMPT !!! ---\n"
            f"Critter ID {critter.id} was already marked for death this tick.\n"
            f"A second death was triggered by: {cause.name}.\n"
        )

    # If it's a new death, add it to our log for this tick
    deaths_this_tick.add(critter.id)

    logger.info(f"    {critter.id} died of {cause.name}")

    dead_critter = DeadCritter(
        original_id=critter.id,
        age=critter.age,
        cause=cause,
        speed=critter.speed,
        size=critter.size,
        player_id=critter.player_id,
        parent_one_id=critter.parent_one_id,
        parent_two_id=critter.parent_two_id,
    )
    session.add(dead_critter)
    session.delete(critter)


def _reproduce(parent1, parent2, session):
    """Creates a new offspring from two parents"""
    logger.info(f"  {parent1} and {parent2} are breeding")

    child_speed = random.choice([parent1.speed, parent2.speed])
    child_size = random.choice([parent1.size, parent2.size])

    if random.random() < MUTATION_CHANCE:
        child_speed += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)
        child_speed = max(child_speed, 1.0)
    if random.random() < MUTATION_CHANCE:
        child_size += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)
        child_size = max(child_size, 1.0)

    child = Critter(
        parent_one_id=parent1.id,
        parent_two_id=parent2.id,
        diet=parent1.diet,
        x=parent1.x,
        y=parent1.y,
        speed=child_speed,
        size=child_size,
    )
    session.add(child)

    parent1.energy -= BREEDING_ENERGY_COST
    parent2.energy -= BREEDING_ENERGY_COST
    parent1.breeding_cooldown = BREEDING_COOLDOWN_TICKS
    parent2.breeding_cooldown = BREEDING_COOLDOWN_TICKS


def _record_statistics(session):
    """Calculates and saves the current sim stats"""
    critters = session.query(Critter).all()
    population = len(critters)
    if population == 0:
        logger.warning("No living critters")
        return

    herbivores = 0
    carnivores = 0
    ages = {}
    health_bins = {"Healthy": 0, "Hurt": 0, "Critical": 0}
    hunger_bins = {}
    thirst_bins = {}
    energies = {}

    for c in critters:
        if c.diet == DietType.HERBIVORE:
            herbivores += 1
        elif c.diet == DietType.CARNIVORE:
            carnivores += 1
        else:
            raise RuntimeError(f"unknown diet type: {c.diet}")

        if not c.age in ages:
            ages[c.age] = 0
        ages[c.age] += 1

        if c.health > 70:
            health_bins["Healthy"] += 1
        elif c.health > 30:
            health_bins["Hurt"] += 1
        else:
            health_bins["Critical"] += 1

        hunger_bin = int(math.floor(c.hunger))
        if not hunger_bin in hunger_bins:
            hunger_bins[hunger_bin] = 0
        hunger_bins[hunger_bin] += 1

        thirst_bin = int(math.floor(c.thirst))
        if not thirst_bin in thirst_bins:
            thirst_bins[thirst_bin] = 0
        thirst_bins[thirst_bin] += 1

        energy_bin = int(math.floor(c.energy))
        if not energy_bin in energies:
            energies[energy_bin] = 0
        energies[energy_bin] += 1

    last_stat = (
        session.query(SimulationStats).order_by(SimulationStats.tick.desc()).first()
    )
    current_tick = (last_stat.tick + 1) if last_stat else 1

    stats = SimulationStats(
        tick=current_tick,
        population=population,
        herbivore_population=herbivores,
        carnivore_population=carnivores,
        age_distribution=json.dumps(ages),
        health_distribution=json.dumps(health_bins),
        hunger_distribution=json.dumps(hunger_bins),
        thirst_distribution=json.dumps(thirst_bins),
        energy_distribution=json.dumps(energies),
    )
    session.add(stats)

    logger.info(f"  Recorded stats for tick {current_tick}: {stats.to_dict()}")
