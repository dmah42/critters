from typing import Any, Dict, Optional
from simulation.behaviours.behavior import AIAction, Behavior
from simulation.brain import SENSE_RADIUS, ActionType
from simulation.models import Critter
from simulation.pathfinding import find_path
from simulation.terrain_type import TerrainType
from simulation.world import World


class WaterSeekingBehavior(Behavior):
    def get_action(self, critter: Critter, world: World, _) -> Optional[AIAction]:
        """
        Determines the complete water-related action for a critter.
        Checks for adjacent water first (DRINK), then scans for distant
        water (SEEK_WATER).
        Returns a complete action dictionary, or None.
        """
        # 1. First, check if we are already next to water.
        surroundings = [
            world.get_tile(critter.x + dx, critter.y + dy)
            for dy in [-1, 0, 1]
            for dx in [-1, 0, 1]
            if not (dx == 0 and dy == 0)
        ]
        is_near_water = any(tile.terrain == TerrainType.WATER for tile in surroundings)

        if is_near_water:
            # If we are, the correct action is to DRINK.
            return {"type": ActionType.DRINK}

        # 2. If not adjacent, scan the wider area for water to move towards.
        scan_range = range(-SENSE_RADIUS, SENSE_RADIUS + 1)
        wide_surroundings = [
            world.get_tile(critter.x + sx, critter.y + sy)
            for sy in scan_range
            for sx in scan_range
            if not (sx == 0 and sy == 0)
        ]

        water_tiles = [
            tile for tile in wide_surroundings if tile.terrain == TerrainType.WATER
        ]

        if not water_tiles:
            # No water found in range.  Trigger a move action.
            return None

        # 3. Find the closest accessible land tile next to the water.
        best_target_tile = self._find_closest_shore(critter, world, water_tiles)

        if not best_target_tile:
            # No shoreline found.. Just move.
            return None

        # Path find to it
        start_pos = (critter.x, critter.y)
        end_pos = (best_target_tile.x, best_target_tile.y)

        path = find_path(world, start_pos, end_pos)

        if path and len(path) > 1:
            next_step = path[1]
            return AIAction(
                type=ActionType.MOVE,
                dx=next_step[0] - critter.x,
                dy=next_step[1] - critter.y,
                target=end_pos,
            )

        # If no path was found return None.
        return None

    def _find_closest_shore(self, critter, world, water_tiles):
        """Helper function to find the best land tile adjacent to water."""
        closest_water_tile = min(
            water_tiles,
            key=lambda tile: abs(tile.x - critter.x) + abs(tile.y - critter.y),
        )

        shore_tiles = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                potential_shore_tile = world.get_tile(
                    closest_water_tile.x + dx, closest_water_tile.y + dy
                )
                if potential_shore_tile.terrain != TerrainType.WATER:
                    shore_tiles.append(potential_shore_tile)

        if not shore_tiles:
            return None

        return min(
            shore_tiles,
            key=lambda tile: abs(tile.x - critter.x) + abs(tile.y - critter.y),
        )
