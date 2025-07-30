# tests/test_moving_behaviors.py

import unittest
import sys
import os
import random

from simulation.terrain_type import TerrainType

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.wandering import WanderingBehavior
from simulation.models import DietType


# --- Mock Objects for Testing ---
class MockCritter:
    """A fake Critter for testing movement behaviors."""

    def __init__(self, x, y, vx, vy, diet):
        self.id = random.randint(1, 1000)
        self.x = x
        self.vx = vx
        self.y = y
        self.vy = vy
        self.diet = diet


class MockWorld:
    """A fake world.  No logic required"""

    def __init__(self, water_locations=None):
        self.water_locations = water_locations if water_locations else set()

    def get_tile(self, x, y):
        terrain = TerrainType.GRASS
        if (x, y) in self.water_locations:
            terrain = TerrainType.WATER
        return {"x": x, "y": y, "terrain": terrain}


class TestWanderingBehavior(unittest.TestCase):

    def test_random_wandering_returns_valid_action(self):
        """
        Tests that RandomWanderingBehavior returns a valid WANDER action.
        """
        critter = MockCritter(x=0, y=0, vx=1, vy=1, diet=DietType.CARNIVORE)
        world = MockWorld()
        behavior = WanderingBehavior()

        # Act: Get the action
        action = behavior.get_action(critter, world, [])  # all_critters is not used

        # Assert: Check that the action is a valid wander
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        self.assertIn(action["dx"], [-1, 0, 1])
        self.assertIn(action["dy"], [-1, 0, 1])

    def test_random_wandering_continues_with_momentum(self):
        """
        Tests that a wandering critter with existing velocity will tend
        to continue in the same direction.
        """
        # This critter has momentum moving right (vx=1)
        critter = MockCritter(x=0, y=0, vx=1, vy=0, diet=DietType.CARNIVORE)
        world = MockWorld()
        behavior = WanderingBehavior()

        # Run the action many times. Due to the high probability of continuing,
        # the vast majority of moves should be to the right.
        right_moves = 0
        for _ in range(100):
            action = behavior.get_action(critter, world, [])
            if action["dx"] > 0:
                right_moves += 1

        # Assert that the critter continued its momentum most of the time
        self.assertGreater(right_moves, 70)  # Should be ~80, so >70 is a safe bet

    def test_random_wandering_avoids_water(self):
        """
        Tests that the wandering behavior will not choose a direction that
        leads directly into a water tile.
        """
        critter = MockCritter(x=0, y=0, vx=0, vy=0, diet=DietType.CARNIVORE)
        water_world = MockWorld(
            water_locations={
                (-1, -1),
                (0, -1),
                (1, -1),
                (-1, 0),
                (-1, 1),
                (0, 1),
                (1, 1),
            }
        )
        behavior = WanderingBehavior()

        for _ in range(20):
            action = behavior.get_action(critter, water_world, [])
            self.assertIsNotNone(action)
            # The only possible move is to the right (1, 0)
            self.assertEqual(action["dx"], 1)
            self.assertEqual(action["dy"], 0)


# This allows you to run the tests directly
if __name__ == "__main__":
    unittest.main()
