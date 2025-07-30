# tests/test_behaviors.py

import random
import unittest
import sys
import os

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.fleeing import FleeingBehavior
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

    def get_tile(self, x, y):
        # For this test, we'll just say there's food at (1, 1)
        has_food = 10.0 if x == 1 and y == 1 else 0.0
        return {"x": x, "y": y, "terrain": "grass", "food_available": has_food}


class TestFleeing(unittest.TestCase):

    def setUp(self):
        """Set up common objects for the tests."""
        self.herbivore = MockCritter(x=0, y=0, diet=DietType.HERBIVORE)
        self.carnivore = MockCritter(x=3, y=2, diet=DietType.CARNIVORE)
        self.world = MockWorld()

    def test_fleeing_when_predator_is_near(self):
        """
        Tests that a herbivore correctly flees from a nearby carnivore.
        """
        fleeing_behavior = FleeingBehavior()
        all_critters = [self.herbivore, self.carnivore]

        # Act: Get the action from the behavior module
        action = fleeing_behavior.get_action(self.herbivore, all_critters)

        # Assert: Check that the action is correct
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        # The direction should be away from (3, 2), so (-3, -2)
        self.assertEqual(action["dx"], -3)
        self.assertEqual(action["dy"], -2)

    def test_no_fleeing_when_predator_is_far(self):
        """
        Tests that a herbivore does not flee if the predator is out of range.
        """
        # Move the carnivore far away
        self.carnivore.x = 10
        self.carnivore.y = 10

        fleeing_behavior = FleeingBehavior()
        all_critters = [self.herbivore, self.carnivore]

        action = fleeing_behavior.get_action(self.herbivore, all_critters)

        # Assert that no action was returned
        self.assertIsNone(action)


# This allows you to run the tests directly with 'python tests/test_behaviors.py'
if __name__ == "__main__":
    unittest.main()
