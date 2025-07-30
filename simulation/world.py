import logging
import noise

from simulation.models import TileState
from simulation.terrain_type import TerrainType

# Elevation noise parameters -- low frequency for large features
# Zoom level: larger == more zoomed
HEIGHT_SCALE = 200.0
# Octaves: larger = more rugged
HEIGHT_OCTAVES = 6
# Persistence and lacunarity affect roughness.
HEIGHT_PERSISTENCE = 0.5
HEIGHT_LACUNARITY = 2.0

# Terrain noise parameters -- high frequency for patches of grass
TERRAIN_SCALE = 100.0
TERRAIN_OCTAVES = 3
TERRAIN_PERSISTENCE = 0.5
TERRAIN_LACUNARITY = 2.0


WATER_LEVEL = -0.3
MOUNTAIN_LEVEL = 0.6

DEFAULT_GRASS_FOOD = 10.0
DIRT_TO_GRASS_LEVEL = 0.0

WORLD_CHUNK_SIZE = 32

logger = logging.getLogger(__name__)


class World:
    """
    Represents the game world, procedural generating terrain
    on the fly.  Nothing is stored in memory.
    """

    def __init__(self, seed, session):
        """Initializes the world with a seed for the noise functions."""
        self.seed = seed
        self.session = session
        # Store loaded chunks
        # Format: {(chunk_x, chunk_y): {(tile_x, tile_y): TileState, ...}}
        self._chunk_cache = {}

    def get_tile(self, x, y):
        # Determine which chunk this tile belongs to
        chunk_x = x // WORLD_CHUNK_SIZE
        chunk_y = y // WORLD_CHUNK_SIZE

        if (chunk_x, chunk_y) not in self._chunk_cache:
            self._load_chunk(chunk_x, chunk_y)

        base_tile = self._generate_procedural_tile(x, y)

        saved_state = self._chunk_cache[(chunk_x, chunk_y)].get((x, y))
        if saved_state:
            base_tile["food_available"] = saved_state.food_available

        return base_tile

    def _load_chunk(self, chunk_x, chunk_y):
        """
        Performs a single, efficient batch query to fetch all tile states
        for the given chunk.
        """
        min_x = chunk_x * WORLD_CHUNK_SIZE
        max_x = min_x + (WORLD_CHUNK_SIZE - 1)
        min_y = chunk_y * WORLD_CHUNK_SIZE
        max_y = min_y + (WORLD_CHUNK_SIZE - 1)

        overrides_list = (
            self.session.query(TileState)
            .filter(
                TileState.x.between(min_x, max_x), TileState.y.between(min_y, max_y)
            )
            .all()
        )

        chunk_data = {(tile.x, tile.y): tile for tile in overrides_list}

        self._chunk_cache[(chunk_x, chunk_y)] = chunk_data

        logger.debug(f"Loaded chunk ({chunk_x}, {chunk_y})")

    def _generate_procedural_tile(self, x, y):
        """The core generation logic."""
        height_val = (
            noise.pnoise2(
                x / HEIGHT_SCALE,
                y / HEIGHT_SCALE,
                octaves=HEIGHT_OCTAVES,
                persistence=HEIGHT_PERSISTENCE,
                lacunarity=HEIGHT_LACUNARITY,
                base=self.seed,
            )
            * 1.5
        )

        terrain = None
        if height_val < WATER_LEVEL:
            terrain = TerrainType.WATER
        elif height_val >= MOUNTAIN_LEVEL:
            terrain = TerrainType.MOUNTAIN
        else:
            # If it's land, calculate a second noise value for terrain type ---
            # We add an offset (e.g., 1000) to the seed to ensure this noise map
            # is completely different from the height map.
            terrain_val = noise.pnoise2(
                x / TERRAIN_SCALE,
                y / TERRAIN_SCALE,
                octaves=TERRAIN_OCTAVES,
                persistence=TERRAIN_PERSISTENCE,
                lacunarity=TERRAIN_LACUNARITY,
                base=self.seed + 1000,
            )

            terrain = TerrainType.DIRT  # Default to dirt
            if terrain_val > DIRT_TO_GRASS_LEVEL:
                terrain = TerrainType.GRASS  # Fertile patches of grass

        tile = {
            "x": x,
            "y": y,
            "height": height_val,
            "terrain": terrain,
            "food_available": DEFAULT_GRASS_FOOD if terrain == TerrainType.GRASS else 0,
        }
        return tile
