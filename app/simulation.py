import enum
import noise
from app.models import TileState
from app import db

DEFAULT_GRASS_FOOD = 10.0
GRASS_REGROWTH_RATE = 0.1
DIRT_TO_GRASS_RATIO = 0.2


class TerrainType(enum.Enum):
    WATER = "water"
    GRASS = "grass"
    DIRT = "dirt"
    MOUNTAIN = "mountain"


def run_simulation_tick():
    """Process one tick of the world simulation. Called periodically."""
    print("tick")
    _process_tile_regrowth()
    print("end tick")


def _process_tile_regrowth():
    """
    Finds all depleted grass tiles and handles regrowth.
    If a tile regrows completely, remove the record.
    """
    depleted_tiles = TileState.query.filter(
        TileState.food_available < DEFAULT_GRASS_FOOD
    ).all()

    tiles_to_delete = []

    for tile in depleted_tiles:
        tile.food_available += GRASS_REGROWTH_RATE

        if tile.food_available >= DEFAULT_GRASS_FOOD:
            tiles_to_delete.append(tile)

    for tile in tiles_to_delete:
        db.session.delete(tile)

    db.session.commit()
    print(
        f"Processed regrowth for {len(depleted_tiles)} tiles.  Deleted {len(tiles_to_delete)} tiles"
    )


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
        self.height_scale = 100.0

        # Octaves: larger = more rugged
        self.height_octaves = 6

        # Persistence and lacunarit affect roughness.
        self.height_persistence = 0.5
        self.height_lacunarity = 2.0

        # Terrain noise parameters -- high frequency for patches of grass
        self.terrain_scale = 25.0
        self.terrain_octaves = 4
        self.terrain_persistence = 0.5
        self.terrain_lacunarity = 2.0

        self.water_level = -0.2
        self.mountain_level = 0.6

    def get_tile(self, x, y):
        """
        Gets the properties of a tile at coords (x, y).
        Generated procedurally with overrides from the database.
        """
        base_tile = self._generate_procedural_tile(x, y)
        saved_state = TileState.query.get((x, y))

        if saved_state:
            base_tile["food_available"] = saved_state.food_available

        return base_tile

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

    def _generate_procedural_tile(self, x, y):
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
                base=self.seed + 1000,  # Use a different seed for a different map
            )

            terrain = TerrainType.DIRT  # Default to dirt
            if terrain_val > DIRT_TO_GRASS_RATIO:
                terrain = TerrainType.GRASS  # Fertile patches of grass

        return {
            "x": x,
            "y": y,
            "height": height_val,
            "terrain": terrain,
            "food_available": DEFAULT_GRASS_FOOD if terrain == TerrainType.GRASS else 0,
        }
