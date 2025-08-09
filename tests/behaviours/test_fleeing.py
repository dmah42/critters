# tests/test_behaviors.py

import random
import unittest
import sys
from typing import List, Tuple
import os

from simulation.world import TileData

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.fleeing import FleeingBehavior
from simulation.models import DietType
from simulation.terrain_type import TerrainType

# --- Mock Objects for Testing ---
# We create simple fake objects to simulate the real ones for our tests.


class MockCritter:
    """A fake Critter for testing purposes."""

    def __init__(self, x, y, diet):
        self.id = random.randint(1, 1000)  # Give it a random ID
        self.x = x
        self.y = y
        self.diet = diet
        self.speed = 3.0
        self.perception = 5.0


class MockWorld:
    """A fake World that returns predictable terrain for testing."""

    def __init__(self, water_locations: List[Tuple[int, int]]):
        self.water_locations = water_locations

    def get_tile(self, x, y) -> TileData:
        if (x, y) in self.water_locations:
            return TileData(
                x=x, y=y, terrain=TerrainType.WATER, height=0.0, food_available=0.0
            )
        return TileData(
            x=x, y=y, terrain=TerrainType.GRASS, height=0.0, food_available=1.0
        )


class TestFleeing(unittest.TestCase):

    def setUp(self):
        """Set up common objects for the tests."""
        self.herbivore = MockCritter(x=0, y=0, diet=DietType.HERBIVORE)
        self.carnivore = MockCritter(x=3, y=2, diet=DietType.CARNIVORE)

    def test_fleeing_when_predator_is_near(self):
        """
        Tests that a herbivore correctly flees from a nearby carnivore.
        """
        self.world = MockWorld(water_locations=[])
        fleeing_behavior = FleeingBehavior()
        all_critters = [self.herbivore, self.carnivore]

        # Act: Get the action from the behavior module
        action = fleeing_behavior.get_action(self.herbivore, self.world, all_critters)

        # Assert: Check that the action is correct
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        # The direction should be away from (3, 2), so (-1, -1)
        self.assertEqual(action["dx"], -1)
        self.assertEqual(action["dy"], -1)

    def test_no_fleeing_when_predator_is_far(self):
        """
        Tests that a herbivore does not flee if the predator is out of range.
        """
        self.world = MockWorld(water_locations=[])
        # Move the carnivore far away
        self.carnivore.x = 10
        self.carnivore.y = 10

        fleeing_behavior = FleeingBehavior()
        all_critters = [self.herbivore, self.carnivore]

        action = fleeing_behavior.get_action(self.herbivore, self.world, all_critters)

        # Assert that no action was returned
        self.assertIsNone(action)

    def test_fleeing_avoids_water_when_predator_is_near(self):
        """
        Tests that a herbivore correctly flees from a nearby carnivore.
        """
        self.world = MockWorld(water_locations=[(-1, -1)])
        fleeing_behavior = FleeingBehavior()
        all_critters = [self.herbivore, self.carnivore]

        # Act: Get the action from the behavior module
        action = fleeing_behavior.get_action(self.herbivore, self.world, all_critters)

        # Assert: Check that the action is correct
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        # The direction should be away from (3, 2) but it can't go to -1,-1 so -1,0 or 0,-1
        self.assertIn(action["dx"], [0, -1])
        self.assertIn(action["dy"], [0, -1])
        self.assertFalse(action["dx"] == -1 and action["dy"] == -1)
        self.assertFalse(action["dx"] == 0 and action["dy"] == 0)


# This allows you to run the tests directly with 'python tests/test_behaviors.py'
if __name__ == "__main__":
    unittest.main()
