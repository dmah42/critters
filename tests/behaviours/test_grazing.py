# tests/test_behaviors.py

import random
import unittest
import sys
import os

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.grazing import GrazingBehavior
from simulation.models import DietType

# --- Mock Objects for Testing ---
# We create simple fake objects to simulate the real ones for our tests.


class MockCritter:
    """A fake Critter for testing purposes."""

    def __init__(self, x, y, diet):
        self.id = random.randint(1, 1000)  # Give it a random ID
        self.x = x
        self.y = y
        self.diet = diet


class MockWorld:
    """A fake World that returns predictable terrain for testing."""

    def generate_tile(self, x, y):
        # For this test, we'll just say there's food at (1, 1)
        has_food = 10.0 if x == 1 and y == 1 else 0.0
        return {"x": x, "y": y, "terrain": "grass", "food_available": has_food}


class TestBehaviors(unittest.TestCase):

    def setUp(self):
        """Set up common objects for the tests."""
        self.herbivore = MockCritter(x=0, y=0, diet=DietType.HERBIVORE)
        self.carnivore = MockCritter(x=2, y=2, diet=DietType.CARNIVORE)
        self.world = MockWorld()

    def test_grazing_finds_food(self):
        """
        Tests that the grazing behavior correctly finds and targets food.
        """
        grazing_behavior = GrazingBehavior()

        # Act: Get the action
        action = grazing_behavior.get_action(self.herbivore, self.world, [])

        # Assert: Check that the action is to seek food at (1, 1)
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.SEEK_FOOD)
        self.assertEqual(action["target"], (1, 1))


# This allows you to run the tests directly with 'python tests/test_behaviors.py'
if __name__ == "__main__":
    unittest.main()
