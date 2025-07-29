# tests/test_moving_behaviors.py

import unittest
import sys
import os
import random

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.wandering import WanderingBehavior
from simulation.models import DietType


# --- Mock Objects for Testing ---
class MockCritter:
    """A fake Critter for testing movement behaviors."""

    def __init__(self, x, y, diet):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y
        self.diet = diet


class TestWanderingBehavior(unittest.TestCase):

    def test_random_wandering_returns_valid_action(self):
        """
        Tests that RandomWanderingBehavior returns a valid WANDER action.
        """
        critter = MockCritter(x=0, y=0, diet=DietType.CARNIVORE)
        behavior = WanderingBehavior()

        # Act: Get the action
        action = behavior.get_action(critter, [])  # all_critters is not used

        # Assert: Check that the action is a valid wander
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.WANDER)
        self.assertIn(action["dx"], [-1, 0, 1])
        self.assertIn(action["dy"], [-1, 0, 1])
        # Ensure it's not a diagonal move
        self.assertNotEqual(abs(action["dx"]) + abs(action["dy"]), 2)


# This allows you to run the tests directly
if __name__ == "__main__":
    unittest.main()
