import unittest
import sys
import os
import random

from simulation.terrain_type import TerrainType
from simulation.world import TileData

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.behaviours.breeding import BreedingBehavior
from simulation.models import AIState, DietType
from simulation.action_type import ActionType


# --- Mock Objects for Testing ---
class MockCritter:
    """A fake Critter for testing breeding logic."""

    def __init__(
        self,
        x,
        y,
        diet=DietType.HERBIVORE,
        health=100.0,
        energy=100.0,
        hunger=0.0,
        thirst=0.0,
        cooldown=0,
        ai_state=AIState.IDLE,
    ):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y
        self.diet = diet
        self.health = health
        self.energy = energy
        self.hunger = hunger
        self.thirst = thirst
        self.breeding_cooldown = cooldown
        self.ai_state = ai_state


class MockWorld:
    """A mock world that provides height and energy cost for pathfinding."""

    def get_tile(self, x, y) -> TileData:
        # For these tests, we can assume all tiles are flat land
        return TileData(
            x=x, y=y, terrain=TerrainType.GRASS, height=0.0, food_available=1.0
        )


class TestBreeding(unittest.TestCase):

    def setUp(self):
        """Create a mock world instance for all tests to use."""
        self.world = MockWorld()

    def test_returns_breed_action_for_adjacent_ready_mate(self):
        """
        Should return a BREED action if a suitable mate is right next to the critter.
        """
        critter = MockCritter(x=0, y=0)
        # This mate is adjacent and meets all breeding criteria
        ready_mate = MockCritter(x=1, y=0)
        all_critters = [critter, ready_mate]

        behavior = BreedingBehavior()
        action = behavior.get_action(critter, self.world, all_critters)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.BREED)
        self.assertEqual(action["partner"], ready_mate)

    def test_returns_move_action_for_nearby_ready_mate(self):
        """
        Should return a MOVE action if a suitable mate is close but not adjacent.
        """
        critter = MockCritter(x=0, y=0)
        # This mate is 2 tiles away and meets all criteria
        nearby_mate = MockCritter(x=2, y=0)
        all_critters = [critter, nearby_mate]

        behavior = BreedingBehavior()
        action = behavior.get_action(critter, self.world, all_critters)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        self.assertEqual(action["target"], (nearby_mate.x, nearby_mate.y))

    def test_returns_none_if_mate_is_not_ready(self):
        """
        Should return None if the only nearby mate is not healthy enough to breed.
        """
        critter = MockCritter(x=0, y=0)
        # This mate is close, but its health is too low
        unhealthy_mate = MockCritter(x=1, y=0, health=50.0)
        all_critters = [critter, unhealthy_mate]

        behavior = BreedingBehavior()
        action = behavior.get_action(critter, self.world, all_critters)

        self.assertIsNone(action)

    def test_returns_none_if_no_mates_in_range(self):
        """
        Should return None if there are no potential mates within the courtship radius.
        """
        critter = MockCritter(x=0, y=0)
        far_away_mate = MockCritter(x=10, y=10)
        all_critters = [critter, far_away_mate]

        behavior = BreedingBehavior()
        action = behavior.get_action(critter, self.world, all_critters)

        self.assertIsNone(action)
