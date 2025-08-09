import random
from typing import Any, Dict, Optional
from simulation.behaviours.behavior import AIAction
from simulation.behaviours.foraging import ForagingBehavior
from simulation.brain import SENSE_RADIUS, ActionType
from simulation.models import Critter
from simulation.pathfinding import find_path
from simulation.terrain_type import TerrainType
from simulation.world import World

# 70% chance to go for the most food instead of the nearest
STRATEGIST_PROBABILITY = 0.7

# Don't even think about tiles with less than this amount of grass.
MINIMUM_GRAZE_AMOUNT = 1.0


class GrazingBehavior(ForagingBehavior):
    def get_action(self, critter: Critter, world: World, _) -> Optional[AIAction]:
        """
        Determines the complete foraging action for a herbivore.
        Checks for food on the current tile first (EAT), then scans for
        distant food (SEEK_FOOD).
        Returns a complete action dictionary, or None.
        """
        # 1. First, check if we are on a tile with food.
        current_tile = world.get_tile(critter.x, critter.y)

        if (
            current_tile.terrain == TerrainType.GRASS
            and current_tile.food_available > MINIMUM_GRAZE_AMOUNT
        ):
            # If so, the correct action is to EAT.
            return AIAction(type=ActionType.EAT)

        # 2. If not on a food tile, scan the wider area to move towards.
        scan_range = range(-SENSE_RADIUS, SENSE_RADIUS + 1)
        surroundings = [
            world.get_tile(critter.x + sx, critter.y + sy)
            for sy in scan_range
            for sx in scan_range
            if not (sx == 0 and sy == 0)
        ]

        food_tiles = [
            tile for tile in surroundings if tile.food_available > MINIMUM_GRAZE_AMOUNT
        ]

        if food_tiles:
            # Choose a foraging strategy (unchanged)
            if random.random() < STRATEGIST_PROBABILITY:
                # Strategist: go for the most food
                best_tile = max(food_tiles, key=lambda tile: tile.food_available)
            else:
                # Opportunist: go for the closest food
                best_tile = min(
                    food_tiles,
                    key=lambda tile: abs(tile.x - critter.x) + abs(tile.y - critter.y),
                )

            # Find a path to the tile
            end_pos = (best_tile.x, best_tile.y)
            path = find_path(world, (critter.x, critter.y), end_pos)

            if path and len(path) > 1:
                # The next step is the second element
                next_step = path[1]

                return AIAction(
                    type=ActionType.MOVE,
                    dx=next_step[0] - critter.x,
                    dy=next_step[1] - critter.y,
                    target=end_pos,
                )

        # 3. If no action can be taken, return None.
        return None
