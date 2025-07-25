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
BASE_ENERGY_COST_PER_MOVE = 1.0
UPHILL_ENERGY_MULTIPLIER = 1.5
DOWNHILL_ENERGY_MULTIPLIER = 0.75


class TerrainType(enum.Enum):
    WATER = "water"
    GRASS = "grass"
    DIRT = "dirt"
    MOUNTAIN = "mountain"


def run_simulation_tick(world, session):
    """Process one tick of the world simulation. Called periodically."""
    print("tick")
    _process_tile_regrowth(session)
    _process_critter_ai(world, session)
    print("end tick")


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
        # Update basic needs
        critter.hunger += HUNGER_PER_TICK
        critter.thirst += THIRST_PER_TICK

        current_tile = world.generate_tile(critter.x, critter.y)

        # TODO: have their needs hit thresholds?
        # TODO: can they smell something nearby?

        for i in range(critter.speed):
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            new_x, new_y = critter.x + dx, critter.y + dy

            destination_tile = world.generate_tile(new_x, new_y)

            # Don't move into water
            # TODO: drink if next to water and it's needed
            if destination_tile["terrain"] != TerrainType.WATER:
                height_diff = destination_tile["height"] - current_tile["height"]
                energy_cost = BASE_ENERGY_COST_PER_MOVE
                if height_diff > 0:
                    energy_cost += height_diff * UPHILL_ENERGY_MULTIPLIER
                elif height_diff < 0:
                    energy_cost += height_diff * DOWNHILL_ENERGY_MULTIPLIER

                critter.energy -= energy_cost

                critter.x = new_x
                critter.y = new_y

    print(f"Processed AI for {len(all_critters)} critters.")


class World:
    """
    Represents the game world, procedurall generating terrain
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
