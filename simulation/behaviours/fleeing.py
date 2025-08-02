import logging
from typing import Any, Dict, List
from simulation.behaviours.behavior import Behavior
from simulation.brain import SENSE_RADIUS, ActionType
from simulation.models import Critter, DietType
from simulation.pathfinding import find_path
from simulation.terrain_type import TerrainType
from simulation.world import World

logger = logging.getLogger(__name__)


class FleeingBehavior(Behavior):
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Dict[str, Any]:
        """
        Scans for nearby predators. If one is found, returns a FLEE action.
        Otherwise, returns None.
        """
        nearby_carnivores = [
            other
            for other in all_critters
            if other.diet == DietType.CARNIVORE
            and abs(other.x - critter.x) <= SENSE_RADIUS
            and abs(other.y - critter.y) <= SENSE_RADIUS
        ]

        if nearby_carnivores:
            closest_predator = min(
                nearby_carnivores,
                key=lambda c: abs(c.x - critter.x) + abs(c.y - critter.y),
            )

            # find a tile that is land and furthest away from the predator
            # within speed range.
            max_range = int(critter.speed)
            possible_escape_tiles = [
                world.get_tile(critter.x + sx, critter.y + sy)
                for sx in range(-max_range, max_range + 1)
                for sy in range(-max_range, max_range + 1)
                if not (sx == 0 and sy == 0)
            ]

            possible_escape_land_tiles = [
                tile
                for tile in possible_escape_tiles
                if tile["terrain"] != TerrainType.WATER
            ]

            if len(possible_escape_land_tiles) == 0:
                logger.warning(
                    f"    {critter.id} trying to flee but no escape is possible"
                )
                return None

            best_target_tile = max(
                possible_escape_land_tiles,
                key=lambda tile: abs(tile["x"] - closest_predator.x)
                + abs(tile["y"] - closest_predator.y),
            )

            # Path find to it
            start_pos = (critter.x, critter.y)
            end_pos = (best_target_tile["x"], best_target_tile["y"])

            path = find_path(world, start_pos, end_pos)

            if path and len(path) > 1:
                next_step = path[1]
                return {
                    "type": ActionType.MOVE,
                    "dx": next_step[0] - critter.x,
                    "dy": next_step[1] - critter.y,
                    "target": end_pos,
                    "predator": closest_predator,
                }

            # If no path was found just run away.
            return {
                "type": ActionType.MOVE,
                "dx": critter.x - closest_predator.x,
                "dy": critter.y - closest_predator.y,
                "predator": closest_predator,
            }

        # If no predators are nearby, return None.
        return None
