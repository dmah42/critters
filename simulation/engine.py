import enum
import json
import math
import random
import noise
from simulation.models import (
    CauseOfDeath,
    Critter,
    DeadCritter,
    DietType,
    SimulationStats,
    TileState,
)
from web_server import db

# Terrain constants
DEFAULT_GRASS_FOOD = 10.0
GRASS_REGROWTH_RATE = 0.1
DIRT_TO_GRASS_RATIO = 0.0

# Critter constants
HUNGER_PER_TICK = 0.1
THIRST_PER_TICK = 0.15
BASE_ENERGY_COST_PER_MOVE = 0.1
UPHILL_ENERGY_MULTIPLIER = 1.5
DOWNHILL_ENERGY_MULTIPLIER = 0.75
SENSE_RADIUS = 5
# 70% chance to go for the most food instead of the nearest
STRATEGIST_PROBABILITY = 0.7

# AI constants
HUNGER_TO_START_FORAGING = 25.0
HUNGER_RESTORED_PER_EAT = 10.0
EAT_AMOUNT = 5.0

ENERGY_TO_START_RESTING = 30.0
ENERGY_REGEN_PER_TICK = 5.0
MAX_ENERGY = 100.0

THIRST_TO_START_DRINKING = 20.0
DRINK_AMOUNT = 25.0

HEALTH_DAMAGE_PER_TICK = 0.5
CRITICAL_HUNGER = 80.0
CRITICAL_THIRST = 75.0

## Breeding constants
HEALTH_TO_BREED = 90.0
MAX_HUNGER_TO_BREED = 15.0
MAX_THIRST_TO_BREED = 15.0
BREEDING_ENERGY_COST = 40.0
BREEDING_COOLDOWN_TICKS = 500
MUTATION_CHANCE = 0.1
MUTATION_AMOUNT = 0.2


class TerrainType(enum.Enum):
    WATER = "water"
    GRASS = "grass"
    DIRT = "dirt"
    MOUNTAIN = "mountain"


def run_simulation_tick(world, session):
    """Process one tick of the world simulation. Called periodically."""
    print("+")
    _process_tile_regrowth(session)
    _process_critter_ai(world, session)
    _record_statistics(session)
    print(".")


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

    print(
        f"Processed regrowth for {len(depleted_tiles)} tiles.  Deleted {len(tiles_to_delete)} tiles"
    )


def _process_critter_ai(world, session):
    """Handles the state changes and actions for living critters"""
    all_critters = session.query(Critter).all()

    if not all_critters:
        print("No living critters found.")
        return

    for critter in all_critters:
        _run_critter_logic(critter, world, session, all_critters)

    print(f"Processed AI for {len(all_critters)} critters.")


def _run_critter_logic(critter, world, session, all_critters):
    """Run the AI logic for a single critter"""
    print(f"  Processing critter {critter.id}")
    # Update basic needs
    critter.age += 1
    critter.hunger += HUNGER_PER_TICK
    critter.thirst += THIRST_PER_TICK
    if critter.breeding_cooldown > 0:
        critter.breeding_cooldown -= 1

    if critter.hunger > CRITICAL_HUNGER or critter.thirst > CRITICAL_THIRST:
        critter.health -= HEALTH_DAMAGE_PER_TICK

    # Check for death
    if critter.health <= 0:
        cause = (
            CauseOfDeath.STARVATION
            if critter.hunger > critter.thirst
            else CauseOfDeath.THIRST
        )
        _handle_death(critter, cause, session)
        return

    # Check in on critter state
    is_tired = critter.energy < ENERGY_TO_START_RESTING
    is_thirsty = critter.thirst >= THIRST_TO_START_DRINKING
    is_hungry = critter.hunger >= HUNGER_TO_START_FORAGING

    # Priority 1: Rest if tired
    if is_tired:
        critter.energy += ENERGY_REGEN_PER_TICK
        critter.energy = min(critter.energy, MAX_ENERGY)
        print(f"    rested: energy: {critter.energy}")
        return

    current_tile = world.generate_tile(critter.x, critter.y)

    # Priority 2: Drink if thirsty and near a water tile
    if is_thirsty:
        surroundings = [
            world.generate_tile(critter.x + dx, critter.y + dy)
            for dy in [-1, 0, 1]
            for dx in [-1, 0, 1]
            if not (dx == 0 and dy == 0)
        ]
        is_near_water = any(
            tile["terrain"] == TerrainType.WATER for tile in surroundings
        )

        if is_near_water:
            critter.thirst -= DRINK_AMOUNT
            critter.thirst = max(critter.thirst, 0)
            print(f"    drank. thirst: {critter.thirst}")
            return

    # Priority 3: Eat if hungry and on a food tile
    if (
        is_hungry
        and current_tile["terrain"] == TerrainType.GRASS
        and current_tile["food_available"] > 0
    ):
        amount_to_eat = min(current_tile["food_available"], EAT_AMOUNT)
        new_tile_food = current_tile["food_available"] - amount_to_eat
        world.update_tile_food(critter.x, critter.y, new_tile_food)

        critter.hunger -= (amount_to_eat / EAT_AMOUNT) * HUNGER_RESTORED_PER_EAT
        critter.hunger = max(critter.hunger, 0)

        print(f"    ate. hunger: {critter.hunger}")
        return

    # If we didn't eat we'll move, towards water or food if necessary.
    dx, dy = 0, 0
    sense_surroundings = [
        world.generate_tile(critter.x + dx, critter.y + dy)
        for dy in range(-SENSE_RADIUS, SENSE_RADIUS + 1)
        for dx in range(-SENSE_RADIUS, SENSE_RADIUS + 1)
        if not (dx == 0 and dy == 0)
    ]

    if is_thirsty:
        # Try to find water
        print(f"    thirsty")
        water_tiles = [
            tile for tile in sense_surroundings if tile["terrain"] == TerrainType.WATER
        ]
        if water_tiles:
            # Find the nearest tile by manhattan distance.
            best_tile = min(
                water_tiles,
                key=lambda tile: abs(tile["x"] - critter.x)
                + abs(tile["y"] - critter.y),
            )
            dx, dy = best_tile["x"] - critter.x, best_tile["y"] - critter.y
            print(f"    found water in {best_tile}")
        else:
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])

    if is_hungry:
        print(f"    hungry")
        # Find the best tile
        food_tiles = [tile for tile in sense_surroundings if tile["food_available"] > 0]

        if food_tiles:
            # Choose a foraging strategy
            if random.random() < STRATEGIST_PROBABILITY:
                # Strategist: go for the most food
                print(f"      going for most food")
                best_tile = max(food_tiles, key=lambda tile: tile["food_available"])
            else:
                # Opportunist: go for closest food by manhattan distance
                print(f"      going for nearest food")
                best_tile = min(
                    food_tiles,
                    key=lambda tile: abs(tile["x"] - critter.x)
                    + abs(tile["y"] - critter.y),
                )

            dx, dy = best_tile["x"] - critter.x, best_tile["y"] - critter.y
            print(f"    found food in {best_tile}")
        else:
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
    else:
        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])

    # Priority 4: Seek a mate
    ready_to_breed = (
        critter.health >= HEALTH_TO_BREED
        and critter.hunger < MAX_HUNGER_TO_BREED
        and critter.thirst < MAX_THIRST_TO_BREED
        and critter.breeding_cooldown == 0
    )

    if ready_to_breed:
        potential_mates = [
            other
            for other in all_critters
            if other.id != critter.id
            and other.diet == critter.id
            and abs(other.x - critter.x) <= SENSE_RADIUS
            and abs(other.y - critter.y) <= SENSE_RADIUS
            and other.health >= HEALTH_TO_BREED
            and other.hunger < MAX_HUNGER_TO_BREED
            and other.thirst < MAX_THIRST_TO_BREED
            and other.breeding_cooldown == 0
        ]

        if potential_mates:
            mate = potential_mates[0]
            if abs(mate.x - critter.x) <= 1 and abs(mate.y - critter.y) <= 1:
                _reproduce(critter, mate, session)
                return
            else:
                dx, dy = mate.x - critter.x, mate.y - critter.y

    # Execute the move
    for _ in range(int(critter.speed)):
        new_x, new_y = critter.x + dx, critter.y + dy
        destination_tile = world.generate_tile(new_x, new_y)

        # Don't move into water
        if destination_tile["terrain"] == TerrainType.WATER:
            print("    stopping due to water")
            break

        if (
            is_hungry
            and destination_tile["terrain"] == TerrainType.GRASS
            and destination_tile["food_available"] > 0
        ):
            print("    stopping due to food")
            break

        height_diff = destination_tile["height"] - current_tile["height"]
        energy_cost = BASE_ENERGY_COST_PER_MOVE
        if height_diff > 0:
            energy_cost += height_diff * UPHILL_ENERGY_MULTIPLIER
        elif height_diff < 0:
            energy_cost += height_diff * DOWNHILL_ENERGY_MULTIPLIER

        critter.energy -= energy_cost

        critter.x = new_x
        critter.y = new_y

    print(f"    energy: {critter.energy}")


def _handle_death(critter, cause, session):
    """Handles the death of a critter"""
    print(f"    died of {cause.name}")

    dead_critter = DeadCritter(
        original_id=critter.id,
        age=critter.age,
        cause=critter.cause,
        speed=critter.speed,
        size=critter.size,
        player_id=critter.player_id,
        parent_one_id=critter.parent_one_id,
        parent_two_id=critter.parent_two_id,
    )
    session.add(dead_critter)
    session.delete(critter)


class World:
    """
    Represents the game world, procedural generating terrain
    on the fly.  Nothing is stored in memory.
    """

    def __init__(self, seed):
        """Initializes the world with a seed for the noise functions."""
        self.seed = seed

        # Elevation noise parameters -- low frequency for large features
        # Zoom level: larger == more zoomed
        self.height_scale = 200.0

        # Octaves: larger = more rugged
        self.height_octaves = 6

        # Persistence and lacunarit affect roughness.
        self.height_persistence = 0.5
        self.height_lacunarity = 2.0

        # Terrain noise parameters -- high frequency for patches of grass
        self.terrain_scale = 100.0
        self.terrain_octaves = 3
        self.terrain_persistence = 0.5
        self.terrain_lacunarity = 2.0

        self.water_level = -0.3
        self.mountain_level = 0.6

    def update_tile_food(self, x, y, new_food_value):
        """
        Updates the food value for a specific tile and saves it to the db.
        """
        tile = TileState.query.get((x, y))
        if tile:
            tile.food_available = new_food_value
        else:
            tile = TileState(x=x, y=y, food_available=new_food_value)
            db.session.add(tile)

        db.session.commit()

    def generate_tile(self, x, y):
        """The core generation logic."""
        height_val = (
            noise.pnoise2(
                x / self.height_scale,
                y / self.height_scale,
                octaves=self.height_octaves,
                persistence=self.height_persistence,
                lacunarity=self.height_lacunarity,
                base=self.seed,
            )
            * 1.5
        )

        terrain = None
        if height_val < self.water_level:
            terrain = TerrainType.WATER
        elif height_val >= self.mountain_level:
            terrain = TerrainType.MOUNTAIN
        else:
            # If it's land, calculate a second noise value for terrain type ---
            # We add an offset (e.g., 1000) to the seed to ensure this noise map
            # is completely different from the height map.
            terrain_val = noise.pnoise2(
                x / self.terrain_scale,
                y / self.terrain_scale,
                octaves=self.terrain_octaves,
                persistence=self.terrain_persistence,
                lacunarity=self.terrain_lacunarity,
                base=self.seed + 1000,
            )

            terrain = TerrainType.DIRT  # Default to dirt
            if terrain_val > DIRT_TO_GRASS_RATIO:
                terrain = TerrainType.GRASS  # Fertile patches of grass

        tile = {
            "x": x,
            "y": y,
            "height": height_val,
            "terrain": terrain,
            "food_available": DEFAULT_GRASS_FOOD if terrain == TerrainType.GRASS else 0,
        }
        return tile


def _record_statistics(session):
    """Calculates and saves the current sim stats"""
    critters = session.query(Critter).all()
    population = len(critters)
    if population == 0:
        print("No living critters")
        return

    herbivores = 0
    carnivores = 0
    ages = {}
    health_bins = {"Healthy": 0, "Hurt": 0, "Critical": 0}
    hunger_bins = {"Sated": 0, "Hungry": 0, "Starving": 0}
    thirst_bins = {"Hydrated": 0, "Thirsty": 0, "Parched": 0}
    energies = {}

    for c in critters:
        if c.diet == DietType.HERBIVORE:
            herbivores += 1
        elif c.diet == DietType.CARNIVORE:
            carnivores += 1
        else:
            print(f"unknown diet type: {c.diet}")

        if not c.age in ages:
            ages[c.age] = 0
        ages[c.age] += 1

        if c.health > 70:
            health_bins["Healthy"] += 1
        elif c.health > 30:
            health_bins["Hurt"] += 1
        else:
            health_bins["Critical"] += 1

        if c.hunger < HUNGER_TO_START_FORAGING:
            hunger_bins["Sated"] += 1
        elif c.hunger < CRITICAL_HUNGER:
            hunger_bins["Hungry"] += 1
        else:
            hunger_bins["Starving"] += 1

        if c.thirst < THIRST_TO_START_DRINKING:
            thirst_bins["Hydrated"] += 1
        elif c.thirst < CRITICAL_THIRST:
            thirst_bins["Thirsty"] += 1
        else:
            thirst_bins["Parched"] += 1

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

    print(f" Recorded stats for tick {current_tick}: {stats.to_dict()}")


def _reproduce(parent1, parent2, session):
    """Creates a new offspring from two parents"""
    print(f"  {parent1} and {parent2} are breeding")

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
