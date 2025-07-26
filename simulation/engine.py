import enum
import random
import noise
from simulation.models import Critter, TileState
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

    for critter in all_critters:
        print(f"  Processing critter {critter.id}")
        # Update basic needs
        critter.hunger += HUNGER_PER_TICK
        critter.thirst += THIRST_PER_TICK

        # Check in on critter state
        is_tired = critter.energy < ENERGY_TO_START_RESTING
        is_thirsty = critter.thirst >= THIRST_TO_START_DRINKING
        is_hungry = critter.hunger >= HUNGER_TO_START_FORAGING

        # Priority 1: Rest if tired
        if is_tired:
            critter.energy += ENERGY_REGEN_PER_TICK
            critter.energy = min(critter.energy, MAX_ENERGY)
            print(f"    rested: energy: {critter.energy}")
            continue

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
                continue

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
            continue

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
                tile
                for tile in sense_surroundings
                if tile["terrain"] == TerrainType.WATER
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
            food_tiles = [
                tile for tile in sense_surroundings if tile["food_available"] > 0
            ]

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

    print(f"Processed AI for {len(all_critters)} critters.")


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
