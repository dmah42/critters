# tests/test_behaviors.py

import random
import unittest
import sys
import os

from simulation.terrain_type import TerrainType
from simulation.world import TileData

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.grazing import MINIMUM_GRAZE_AMOUNT, GrazingBehavior
from simulation.models import DietType

# --- Mock Objects for Testing ---
# We create simple fake objects to simulate the real ones for our tests.


class MockCritter:
    """A fake Critter for testing purposes."""

    def __init__(self, x, y, diet=DietType.HERBIVORE):
        self.id = random.randint(1, 1000)  # Give it a random ID
        self.x = x
        self.y = y
        self.diet = diet


class MockWorld:
    """A fake World that returns predictable terrain for testing."""

    def __init__(self, food_locations):
        # food_locations should be a dict like {(x, y): amount}
        self.food_locations = food_locations

    def get_tile(self, x, y) -> TileData:
        food_amount = self.food_locations.get((x, y), 0.0)
        return TileData(
            x=x,
            y=y,
            terrain=TerrainType.GRASS,
            food_available=food_amount,
            height=y,
        )


class TestBehaviors(unittest.TestCase):

    def test_eats_when_on_sufficient_food(self):
        """
        Tests that the behavior returns an EAT action if the critter is
        on a tile with enough food.
        """
        critter = MockCritter(x=0, y=0)
        # The critter is at (0,0) where there is plenty of food
        world = MockWorld(food_locations={(0, 0): 10.0})
        behavior = GrazingBehavior()

        # Act: Get the action
        action = behavior.get_action(critter, world, [])

        # Assert: The action should be EAT
        self.assertIsNotNone(action)
        self.assertEqual(action.type, ActionType.EAT)

    def test_moves_towards_best_food_source(self):
        """
        Tests that the behavior returns a MOVE action towards a food source.
        """
        critter = MockCritter(x=0, y=0)
        # There is a good food source at (3, 3)
        world = MockWorld(food_locations={(3, 3): 10.0})
        behavior = GrazingBehavior()

        action = behavior.get_action(critter, world, [])

        # Assert: The action should be MOVE with the correct target
        self.assertIsNotNone(action)
        self.assertEqual(action.type, ActionType.MOVE)
        self.assertEqual(action.target, (3, 3))

    def test_ignores_insufficient_food(self):
        """
        Tests that the behavior ignores food sources that are below the
        MINIMUM_GRAZE_AMOUNT threshold.
        """
        critter = MockCritter(x=0, y=0)
        # The only food source has a negligible amount of food
        world = MockWorld(food_locations={(3, 3): MINIMUM_GRAZE_AMOUNT - 0.1})
        behavior = GrazingBehavior()

        action = behavior.get_action(critter, world, [])

        # Assert: No action should be taken as the food is not worth it
        self.assertIsNone(action)


# This allows you to run the tests directly with 'python tests/test_behaviors.py'
if __name__ == "__main__":
    unittest.main()
