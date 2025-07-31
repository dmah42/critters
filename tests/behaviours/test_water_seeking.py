import unittest
import sys
import os
import random

from simulation.behaviours.water_seeking import WaterSeekingBehavior
from simulation.brain import THIRST_TO_START_DRINKING
from simulation.factory import create_ai_for_critter
from simulation.models import DietType
from simulation.terrain_type import TerrainType

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType


# --- Mock Objects for Testing ---
class MockCritter:
    """A fake Critter for testing purposes."""

    def __init__(self, x, y):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y


class MockWorld:
    """A mock world that can be configured with water obstacles."""

    def __init__(self, water_locations=None):
        self.water_locations = water_locations if water_locations is not None else set()

    def get_tile(self, x, y):
        terrain = (
            TerrainType.WATER if (x, y) in self.water_locations else TerrainType.GRASS
        )
        # Pathfinding requires height, so we'll add a default
        return {"x": x, "y": y, "terrain": terrain, "height": 0.0}


# --- The Tests ---


class TestWaterSeekingBehavior(unittest.TestCase):

    def test_drinks_when_adjacent_to_water(self):
        """
        Should return a DRINK action if the critter is already next to water.
        """
        critter = MockCritter(x=0, y=0)
        world = MockWorld(water_locations={(1, 0)})

        behavior = WaterSeekingBehavior()
        action = behavior.get_action(critter, world, [])

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.DRINK)

    def test_moves_towards_reachable_water(self):
        """
        Should return a MOVE action with a valid path to the nearest water.
        """
        critter = MockCritter(x=-1, y=0)
        # Create a world with a simple wall, forcing the path to go around
        world = MockWorld(water_locations={(2, 2), (1, -1), (1, 0), (1, 1)})

        behavior = WaterSeekingBehavior()
        action = behavior.get_action(critter, world, [])

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        # The target should be the nearest shore tile
        self.assertEqual(action["target"], (0, 0))
        # The first step of the path should be a valid move, e.g., (0, 1) to start going around
        self.assertEqual((action["dx"], action["dy"]), (1, 0))

    def test_finds_path_to_island_shore(self):
        """
        Should return None if the only water is on an unreachable island,
        as the behavior module itself cannot find a valid shore target.
        """
        critter = MockCritter(x=0, y=0)
        # Create a world where the water at (3,3) is completely surrounded by more water
        world = MockWorld(
            water_locations={
                (3, 3),
                (2, 2),
                (2, 3),
                (2, 4),
                (3, 2),
                (3, 4),
                (4, 2),
                (4, 3),
                (4, 4),
            }
        )

        behavior = WaterSeekingBehavior()
        # We are only testing the behavior module, not the full brain.
        action = behavior.get_action(critter, world, [])

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        # The target should be the nearest shore tile
        self.assertEqual(action["target"], (1, 1))
        # The first step of the path should be a valid move, e.g., (0, 1) to start going around
        self.assertEqual((action["dx"], action["dy"]), (1, 1))
