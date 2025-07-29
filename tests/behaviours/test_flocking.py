# tests/test_moving_behaviors.py

import unittest
import sys
import os
import random

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.flocking import FlockingBehavior
from simulation.models import DietType


# --- Mock Objects for Testing ---
class MockCritter:
    """A fake Critter for testing movement behaviors."""

    def __init__(self, x, y, vx, vy, diet):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.diet = diet


class TestFlockingBehavior(unittest.TestCase):

    def test_flocking_returns_none_with_no_flockmates(self):
        """
        Tests that FlockingBehavior returns None if there are no nearby flockmates.
        """
        critter = MockCritter(x=0, y=0, vx=0, vy=0, diet=DietType.HERBIVORE)
        behavior = FlockingBehavior()

        action = behavior.get_action(critter, [critter])  # Only itself in the list

        self.assertIsNone(action)

    def test_flocking_cohesion_moves_towards_center(self):
        """
        Tests the Cohesion rule: a critter should move towards the center of its flock.
        """
        critter = MockCritter(x=0, y=0, vx=0, vy=0, diet=DietType.HERBIVORE)
        # Place all flockmates in a cluster far away
        flockmates = [
            MockCritter(x=5, y=5, vx=1, vy=-1, diet=DietType.HERBIVORE),
            MockCritter(x=6, y=5, vx=1, vy=-1, diet=DietType.HERBIVORE),
        ]
        all_critters = [critter] + flockmates
        behavior = FlockingBehavior()

        action = behavior.get_action(critter, all_critters)

        # Assert: The direction should be positive on both axes, towards the flock
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.WANDER)
        self.assertGreater(action["dx"], 0)
        self.assertGreater(action["dy"], 0)

    def test_flocking_separation_moves_away_from_crowd(self):
        """
        Tests the Separation rule: a critter should move away from a very close neighbor.
        """
        critter = MockCritter(x=0, y=0, vx=0, vy=0, diet=DietType.HERBIVORE)
        # Place a single flockmate extremely close
        close_mate = MockCritter(x=1, y=0, vx=-1, vy=0, diet=DietType.HERBIVORE)
        all_critters = [critter, close_mate]
        behavior = FlockingBehavior()

        action = behavior.get_action(critter, all_critters)

        # Assert: The direction should be negative on the x-axis, away from the neighbor
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.WANDER)
        self.assertLess(action["dx"], 0)


# This allows you to run the tests directly
if __name__ == "__main__":
    unittest.main()
