# tests/test_moving_behaviors.py

import unittest
import sys
import os
import random

from simulation.terrain_type import TerrainType
from simulation.world import TileData

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.flocking import FlockingBehavior
from simulation.models import AIState, DietType


# --- Mock Objects for Testing ---
class MockCritter:
    """A fake Critter for testing movement behaviors."""

    def __init__(self, x, y, vx, vy, diet, ai_state=AIState.IDLE):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.diet = diet
        self.ai_state = ai_state


class MockWorld:
    """A fake world with limited functionality"""

    def get_tile(self, x, y) -> TileData:
        return TileData(
            x=x, y=y, terrain=TerrainType.GRASS, height=y, food_available=1.0
        )


class TestFlockingBehavior(unittest.TestCase):

    def test_lone_herbivore_falls_back_to_wandering(self):
        """
        Tests that FlockingBehavior correctly falls back to wandering when a
        critter has no flockmates.
        """
        critter = MockCritter(x=0, y=0, vx=0, vy=0, diet=DietType.HERBIVORE)
        world = MockWorld()
        behavior = FlockingBehavior()

        # Act: Get the action when the critter is alone
        action = behavior.get_action(critter, world, [critter])

        # Assert: The action should now be a valid MOVE action, not None.
        self.assertIsNotNone(action)
        self.assertEqual(action.type, ActionType.MOVE)

    def test_flocking_cohesion_moves_towards_center(self):
        """
        Tests the Cohesion rule: a critter should move towards the center of its flock.
        """
        critter = MockCritter(x=0, y=0, vx=0, vy=0, diet=DietType.HERBIVORE)
        world = MockWorld()
        # Place all flockmates in a cluster far away
        flockmates = [
            MockCritter(x=5, y=5, vx=1, vy=-1, diet=DietType.HERBIVORE),
            MockCritter(x=6, y=5, vx=1, vy=-1, diet=DietType.HERBIVORE),
        ]
        all_critters = [critter] + flockmates
        behavior = FlockingBehavior()

        action = behavior.get_action(critter, world, all_critters)

        # Assert: The direction should be positive on both axes, towards the flock
        self.assertIsNotNone(action)
        self.assertEqual(action.type, ActionType.MOVE)
        self.assertGreater(action.dx, 0)
        self.assertGreater(action.dy, 0)

    def test_flocking_separation_moves_away_from_crowd(self):
        """
        Tests the Separation rule: a critter should move away from a very close neighbor.
        """
        critter = MockCritter(x=0, y=0, vx=0, vy=0, diet=DietType.HERBIVORE)
        world = MockWorld()
        # Place a single flockmate extremely close
        close_mate = MockCritter(x=1, y=0, vx=-1, vy=0, diet=DietType.HERBIVORE)
        all_critters = [critter, close_mate]
        behavior = FlockingBehavior()

        action = behavior.get_action(critter, world, all_critters)

        # Assert: The direction should be negative on the x-axis, away from the neighbor
        self.assertIsNotNone(action)
        self.assertEqual(action.type, ActionType.MOVE)
        self.assertLess(action.dx, 0)

    def test_flocking_separation_is_ignored_for_suitor(self):
        """
        Tests that a critter will NOT flee from a nearby flockmate if that
        flockmate is in the SEEKING_MATE state.
        """
        world = MockWorld()
        # Critter B, the target of the approach
        target_critter = MockCritter(x=0, y=0, vx=1, vy=0, diet=DietType.HERBIVORE)

        # Critter A, the suitor, is very close and in the SEEKING_MATE state
        suitor_critter = MockCritter(
            x=1, y=0, vx=1, vy=0, diet=DietType.HERBIVORE, ai_state=AIState.SEEKING_MATE
        )

        all_critters = [target_critter, suitor_critter]
        behavior = FlockingBehavior()

        # Get the action for the TARGET critter
        action = behavior.get_action(target_critter, world, all_critters)

        # Assert: The target critter should be moving TOWARDS the suitor.
        # It is ignoring the separation rule and still applying cohesion.
        self.assertIsNotNone(action)
        self.assertGreater(action.dx, 0)


# This allows you to run the tests directly
if __name__ == "__main__":
    unittest.main()
