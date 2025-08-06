import json
import logging
import math
import random
from typing import List
from simulation.goal_type import GoalType
from simulation.mapping import GOAL_TO_STATE_MAP
from simulation.terrain_type import TerrainType
from simulation.brain import (
    CRITICAL_HUNGER,
    CRITICAL_THIRST,
    HUNGER_TO_START_FORAGING,
    MAX_ENERGY,
    MAX_HUNGER,
    MAX_THIRST,
    THIRST_TO_START_DRINKING,
    ActionType,
)
from simulation.models import (
    AIState,
    CauseOfDeath,
    Critter,
    CritterEvent,
    DeadCritter,
    DietType,
    Event,
    SimulationStats,
    TileState,
)
from simulation.factory import create_ai_for_critter
from simulation.world import DEFAULT_GRASS_FOOD, World, get_energy_cost
from sqlalchemy.orm import Session


# Terrain constants
GRASS_REGROWTH_RATE = 0.1

# Critter constants
THIRST_PER_TICK = 0.25

# AI constants
HUNGER_RESTORED_PER_GRASS_EATEN = 30.0
HUNGER_RESTORED_PER_PREY_EATEN = 25.0

GRASS_EAT_AMOUNT = 5.0

ENERGY_REGEN_PER_TICK = 5.0

# Base hunger increase per tick, even for an idle critter.
BASE_METABOLIC_RATE = 0.05

# The factor to convert spent energy into hunger.
ENERGY_TO_HUNGER_RATIO = 0.2

# The factor that converts food into energy.
FOOD_TO_ENERGY_RATIO = 8.0

DRINK_AMOUNT = 40.0
THIRST_QUENCHED_PER_EAT = 8.0

# The amount of damage a critter in critical condition takes per tick
HEALTH_DAMAGE_PER_TICK = 0.1
# The amount of health a well-fed critter regens each tick.
HEALTH_REGEN_PER_TICK = 0.2

DAMAGE_PER_SIZE_POINT = 5.0

# A value of 0.8 means a prey with the same speed as
# the attacker has an 80% chance to escape
ESCAPE_CHANCE_MULTIPLIER = 0.8

## Breeding constants
BREEDING_ENERGY_COST = 40.0
BREEDING_COOLDOWN_TICKS = 500
MUTATION_CHANCE = 0.1
MUTATION_AMOUNT = 0.2

logger = logging.getLogger(__name__)


def run_simulation_tick(world: World, session: Session):
    """Process one tick of the world simulation. Called periodically."""
    print(".", end="")
    logger.info("+++ Starting tick +++")
    _process_tile_regrowth(session)
    _process_critter_ai(world, session)
    _record_statistics(session)
    logger.info("+++ Ending tick +++")
    print("|", end="", flush=True)


def _process_tile_regrowth(session: Session):
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


def _process_critter_ai(world: World, session: Session):
    """Handles the state changes and actions for living critters"""
    all_critters = session.query(Critter).all()

    if not all_critters:
        logger.warning("No living critters found.")
        return

    for critter in all_critters:
        if critter.is_ghost:
            logger.info(f"Skipping update for ghost {critter.id}")
            continue
        _run_critter_logic(critter, world, session, all_critters)

    logger.info(f"Processed AI for {len(all_critters)} critters.")


def _run_critter_logic(
    critter: Critter,
    world: World,
    session: Session,
    all_critters: List[Critter],
):
    """
    The main AI dispatcher for a single critter's turn.
    It creates the appropriate AI brain, gets an action, and executes it.
    """
    # --- Part 1: Universal State Updates (Health, Hunger, Death, etc.) ---
    # This initial block of code is the same as before.
    logger.info(f"  Processing critter {critter.id} [{critter.ai_state.name}]")

    # Check for death by old age
    if critter.age > critter.lifespan * 0.8:
        # Chance of dying increases linearly as the critter gets older
        # with a 10% chance to die per tick at 100% of its lifespan
        death_chance = (critter.age / critter.lifespan) * 0.1
        if random.random() < death_chance:
            _handle_death(critter, CauseOfDeath.OLD_AGE, session)
            return

    # A critter can heal if its basic food and water needs are met.
    if (
        critter.hunger < HUNGER_TO_START_FORAGING
        and critter.thirst < THIRST_TO_START_DRINKING
    ):
        critter.health = min(critter.health + HEALTH_REGEN_PER_TICK, critter.max_health)
        logger.info(f"    healing: health: {critter.health:.2f}")

    start_energy: float = critter.energy

    critter.age += 1
    critter.thirst = min(critter.thirst + THIRST_PER_TICK, MAX_THIRST)
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
        _handle_death(critter, cause, session)
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

    critter.last_action = action_type
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
        critter.energy = min(critter.energy + ENERGY_REGEN_PER_TICK, MAX_ENERGY)
        logger.info(f"    rested: energy: {critter.energy:.2f}")

    elif action_type == ActionType.DRINK:
        critter.thirst -= DRINK_AMOUNT
        critter.thirst = max(critter.thirst, 0)
        logger.info(f"    drank: thirst: {critter.thirst}")

    elif action_type == ActionType.EAT:
        current_tile = world.get_tile(critter.x, critter.y)
        amount_to_eat = min(current_tile["food_available"], GRASS_EAT_AMOUNT)
        new_tile_food = current_tile["food_available"] - amount_to_eat
        _update_tile_food(session, critter.x, critter.y, new_tile_food)

        critter.hunger -= (
            amount_to_eat / GRASS_EAT_AMOUNT
        ) * HUNGER_RESTORED_PER_GRASS_EATEN
        critter.hunger = max(critter.hunger, 0)

        energy_gained = amount_to_eat * FOOD_TO_ENERGY_RATIO
        critter.energy = min(critter.energy + energy_gained, MAX_ENERGY)

        thirst_quenched = amount_to_eat * THIRST_QUENCHED_PER_EAT
        critter.thirst = max(critter.thirst - thirst_quenched, 0)

        logger.info(
            f"    ate {amount_to_eat}: "
            f"hunger: {critter.hunger:.2f}, "
            f"thirst: {critter.thirst:.2f}, "
            f"energy: {critter.energy:.2f}"
        )

    elif action_type == ActionType.ATTACK:
        prey = action["target"]

        # Base escape chance on the speed difference.
        escape_chance_modifier = prey.speed / critter.speed
        # There's always a 5% chance the predator wins
        final_escape_chance = min(
            escape_chance_modifier * ESCAPE_CHANCE_MULTIPLIER, 0.95
        )

        if random.random() < final_escape_chance:
            logger.info(f"    attack failed: {prey.id} escaped from {critter.id}")
            _log_event(
                session,
                prey.id,
                prey.age,
                Event.ATTACK_ESCAPED,
                f"Survived attack from {critter.id}",
            )
            # TODO: consider an energy cost for the attack
            # critter.energy -= FAILED_ATTACK_ENERGY_COST
        else:
            damage = critter.size * DAMAGE_PER_SIZE_POINT

            prey.health -= damage

            logger.info(f"    attacked: {prey.id} for {damage:.2f}")

            if prey.health <= 0:
                _handle_death(prey, CauseOfDeath.PREDATION, session)

                hunger_restored = prey.size * HUNGER_RESTORED_PER_PREY_EATEN
                critter.hunger = max(critter.hunger - hunger_restored, 0)

                energy_gained = prey.size * FOOD_TO_ENERGY_RATIO
                critter.energy = min(critter.energy + energy_gained, MAX_ENERGY)

                thirst_quenched = prey.size * THIRST_QUENCHED_PER_EAT
                critter.thirst = max(critter.thirst - thirst_quenched, 0)

                logger.info(
                    f"    kill successful: "
                    f"hunger: {critter.hunger:.2f}, "
                    f"thirst: {critter.thirst:.2f}, "
                    f"energy: {critter.energy:.2f}"
                )
                _log_event(
                    session,
                    critter.id,
                    critter.age,
                    Event.ATTACK_KILLED,
                    f"Killed {prey.id}",
                )
            else:
                logger.info(f"      {prey.id} survived with {prey.health:.2f} health")
                _log_event(
                    session,
                    prey.id,
                    prey.age,
                    Event.ATTACK_SURVIVED,
                    f"Survived attack from {critter.id}",
                )

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
            all_critters,
            action["dx"],
            action["dy"],
            goal,
            target=target,
        )

    else:
        raise NotImplementedError(f"Unimplemented action '{action_type.name}'")

    # Calculate energy spent and correlative hunger. Clamped so we don't apply
    # negative hunger when resting.
    energy_spent: float = max(start_energy - critter.energy, 0)

    hunger_increase = (
        BASE_METABOLIC_RATE + (energy_spent * ENERGY_TO_HUNGER_RATIO)
    ) * critter.metabolism
    critter.hunger = min(critter.hunger + hunger_increase, MAX_HUNGER)


def _update_tile_food(session, x: int, y: int, new_food_value: float):
    """
    Updates the food value for a specific tile and saves it to the session.
    """
    tile = session.query(TileState).get((x, y))
    if tile:
        tile.food_available = new_food_value
    else:
        tile = TileState(x=x, y=y, food_available=new_food_value)
        session.add(tile)


def _execute_move(
    critter: Critter,
    world: World,
    all_critters: List[Critter],
    dx: float,
    dy: float,
    goal: GoalType,
    target=None,
):
    """
    Executes a move with variable speed for a critter, checking for obstacles and goals.
    """
    old_x, old_y = critter.x, critter.y

    # Normalize the direction vector to get single steps
    move_dx = 1 if dx > 0 else -1 if dx < 0 else 0
    move_dy = 1 if dy > 0 else -1 if dy < 0 else 0

    if move_dx == 0 and move_dy == 0:
        critter.vx, critter.vy = 0, 0
        return

    if goal == GoalType.SURVIVE_DANGER or (
        critter.diet == DietType.CARNIVORE and goal == GoalType.SATE_HUNGER
    ):
        # Full speed sprint
        critter.movement_progress += critter.speed
        steps_to_take = int(critter.movement_progress)
        critter.movement_progress -= steps_to_take
    else:
        # Low priority goals use a slower walking pace.
        max_walk_speed = max(1, int(critter.speed))
        steps_to_take = random.randint(1, max_walk_speed)

    hit_obstacle = False

    occupied_positions = {(c.x, c.y) for c in all_critters if c.id != critter.id}

    for _ in range(steps_to_take):
        new_x, new_y = critter.x + move_dx, critter.y + move_dy
        destination_tile = world.get_tile(new_x, new_y)

        # Don't let critters get in the same space or step on water.
        if (
            destination_tile["terrain"] == TerrainType.WATER
            or (new_x, new_y) in occupied_positions
        ):
            logger.info("    unable to move. obstacle.")
            hit_obstacle = True
            break

        current_tile = world.get_tile(critter.x, critter.y)

        energy_cost = get_energy_cost(current_tile, destination_tile)

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


def _handle_death(critter: Critter, cause: CauseOfDeath, session: Session):
    """Handles the death of a critter"""

    # Check that they are not already marked for death
    if critter.is_ghost:
        raise RuntimeError(
            f"--- !!! WARNING: DUPLICATE DEATH ATTEMPT !!! ---\n"
            f"Critter ID {critter.id} was already a ghost this tick.\n"
            f"A second death was triggered by: {cause.name}.\n"
        )

    critter.is_ghost = True

    logger.info(f"    {critter.id} died of {cause.name}")
    description = f"Died of {cause.name}."
    _log_event(session, critter.id, critter.age, Event.DEATH, description)

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


def _reproduce(parent1: Critter, parent2: Critter, session: Session):
    """Creates a new offspring from two parents"""
    logger.info(f"  {parent1} and {parent2} are breeding")

    child_speed = random.choice([parent1.speed, parent2.speed])
    child_size = random.choice([parent1.size, parent2.size])
    child_metabolism = random.choice([parent1.metabolism, parent2.metabolism])
    child_lifespan = random.choice([parent1.lifespan, parent2.lifespan])

    if random.random() < MUTATION_CHANCE:
        child_speed += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)
        child_speed = max(child_speed, 1.0)
    if random.random() < MUTATION_CHANCE:
        child_size += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)
        child_size = max(child_size, 1.0)
    if random.random() < MUTATION_CHANCE:
        child_metabolism += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)
        child_metabolism = max(child_size, 0.5)
    if random.random() < MUTATION_CHANCE:
        child_lifespan += random.randint(-50, 50)
        child_lifespan = max(child_metabolism, 500)

    child = Critter(
        parent_one_id=parent1.id,
        parent_two_id=parent2.id,
        diet=parent1.diet,
        x=parent1.x,
        y=parent1.y,
        speed=child_speed,
        size=child_size,
        metabolism=child_metabolism,
        lifespan=child_lifespan,
    )
    session.add(child)

    _log_event(
        session,
        child.id,
        child.age,
        Event.BIRTH,
        f"Born to parents {parent1.id} and {parent2.id}",
    )
    _log_event(
        session,
        parent1.id,
        parent1.age,
        Event.BREED,
        f"Bred with {parent2.id} to produce {child.id}",
    )
    _log_event(
        session,
        parent2.id,
        parent2.age,
        Event.BREED,
        f"Bred with {parent1.id} to produce {child.id}",
    )

    parent1.energy -= BREEDING_ENERGY_COST
    parent2.energy -= BREEDING_ENERGY_COST
    parent1.breeding_cooldown = BREEDING_COOLDOWN_TICKS
    parent2.breeding_cooldown = BREEDING_COOLDOWN_TICKS


def _record_statistics(session: Session):
    """Calculates and saves the current sim stats"""
    critters = session.query(Critter).all()
    population = len(critters)

    if population == 0:
        logger.warning("No living critters")
        return

    herbivore_stats = {
        "count": 0,
        "ages": {},
        "health": {"Healthy": 0, "Hurt": 0, "Critical": 0},
        "hunger": {},
        "thirst": {},
        "energy": {},
    }
    carnivore_stats = {
        "count": 0,
        "ages": {},
        "health": {"Healthy": 0, "Hurt": 0, "Critical": 0},
        "hunger": {},
        "thirst": {},
        "energy": {},
    }

    goal_bins = {}

    for c in critters:
        stats_dict = (
            herbivore_stats if c.diet == DietType.HERBIVORE else carnivore_stats
        )

        stats_dict["count"] += 1

        stats_dict["ages"][c.age] = stats_dict["ages"].get(c.age, 0) + 1
        hunger_bin = int(math.floor(c.hunger))
        stats_dict["hunger"][hunger_bin] = stats_dict["hunger"].get(hunger_bin, 0) + 1
        thirst_bin = int(math.floor(c.thirst))
        stats_dict["thirst"][thirst_bin] = stats_dict["thirst"].get(thirst_bin, 0) + 1
        energy_bin = int(math.floor(c.energy))
        stats_dict["energy"][energy_bin] = stats_dict["energy"].get(energy_bin, 0) + 1

        if c.health > 70:
            stats_dict["health"]["Healthy"] += 1
        elif c.health > 30:
            stats_dict["health"]["Hurt"] += 1
        else:
            stats_dict["health"]["Critical"] += 1

        goal_bin = c.ai_state.name
        goal_bins[goal_bin] = goal_bins.get(goal_bin, 0) + 1

    last_stat = (
        session.query(SimulationStats).order_by(SimulationStats.tick.desc()).first()
    )
    current_tick = (last_stat.tick + 1) if last_stat else 1

    stats = SimulationStats(
        tick=current_tick,
        population=population,
        herbivore_population=herbivore_stats["count"],
        carnivore_population=carnivore_stats["count"],
        herbivore_age_distribution=json.dumps(herbivore_stats["ages"]),
        carnivore_age_distribution=json.dumps(carnivore_stats["ages"]),
        herbivore_health_distribution=json.dumps(herbivore_stats["health"]),
        carnivore_health_distribution=json.dumps(carnivore_stats["health"]),
        herbivore_hunger_distribution=json.dumps(herbivore_stats["hunger"]),
        carnivore_hunger_distribution=json.dumps(carnivore_stats["hunger"]),
        herbivore_thirst_distribution=json.dumps(herbivore_stats["thirst"]),
        carnivore_thirst_distribution=json.dumps(carnivore_stats["thirst"]),
        herbivore_energy_distribution=json.dumps(herbivore_stats["energy"]),
        carnivore_energy_distribution=json.dumps(carnivore_stats["energy"]),
        goal_distribution=json.dumps(goal_bins),
    )
    session.add(stats)

    logger.info(f"  Recorded stats for tick {current_tick}: {stats.to_dict()}")


def _log_event(
    session: Session, critter_id: int, tick: int, event: Event, description: str
):
    """Creates and saves a new CritterEvent to the session"""
    event = CritterEvent(
        critter_id=critter_id, tick=tick, event=event, description=description
    )
    session.add(event)
