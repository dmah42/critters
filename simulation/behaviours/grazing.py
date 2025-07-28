import random
from simulation.brain import SENSE_RADIUS, ActionType
from simulation.terrain_type import TerrainType

# 70% chance to go for the most food instead of the nearest
STRATEGIST_PROBABILITY = 0.7


class GrazingBehavior:
    def get_action(self, critter, world):
        """
        Determines the complete foraging action for a herbivore.
        Checks for food on the current tile first (EAT), then scans for
        distant food (SEEK_FOOD).
        Returns a complete action dictionary, or None.
        """
        # 1. First, check if we are on a tile with food.
        current_tile = world.generate_tile(critter.x, critter.y)
        if (
            current_tile["terrain"] == TerrainType.GRASS
            and current_tile["food_available"] > 0
        ):
            # If so, the correct action is to EAT.
            return {"type": ActionType.EAT}

        # 2. If not on a food tile, scan the wider area to move towards.
        scan_range = range(-SENSE_RADIUS, SENSE_RADIUS + 1)
        surroundings = [
            world.generate_tile(critter.x + sx, critter.y + sy)
            for sy in scan_range
            for sx in scan_range
            if not (sx == 0 and sy == 0)
        ]

        food_tiles = [tile for tile in surroundings if tile["food_available"] > 0]

        if food_tiles:
            # Choose a foraging strategy (unchanged)
            if random.random() < STRATEGIST_PROBABILITY:
                # Strategist: go for the most food
                best_tile = max(food_tiles, key=lambda tile: tile["food_available"])
            else:
                # Opportunist: go for the closest food
                best_tile = min(
                    food_tiles,
                    key=lambda tile: abs(tile["x"] - critter.x)
                    + abs(tile["y"] - critter.y),
                )

            # If a target is found, the action is to SEEK_FOOD.
            return {
                "type": ActionType.SEEK_FOOD,
                "dx": best_tile["x"] - critter.x,
                "dy": best_tile["y"] - critter.y,
                "target": (best_tile["x"], best_tile["y"]),
            }

        # 3. If no action can be taken, return None.
        return None
