# tests/test_mate_seeking.py

import unittest
import sys
import os
import random

from simulation.world import TileData

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.mate_seeking import MateSeekingBehavior
from simulation.models import DietType


class MockCritter:
    def __init__(self, x, y, diet, health=100.0, hunger=0.0, thirst=0.0, cooldown=0):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y
        self.diet = diet
        self.health = health
        self.hunger = hunger
        self.thirst = thirst
        self.breeding_cooldown = cooldown


class MockWorld:
    """A fake World that returns predictable terrain for testing."""

    def get_tile(self, x, y):
        # For this test, we'll just say there's food at (1, 1)
        has_food = 10.0 if x == 1 and y == 1 else 0.0
        # Also just set the height to be the same as y
        return TileData(
            x=x,
            y=y,
            terrain="grass",
            food_available=has_food,
            height=y,
        )


class TestMateSeekingBehavior(unittest.TestCase):

    def setUp(self):
        self.critter = MockCritter(x=0, y=0, diet=DietType.HERBIVORE)
        self.world = MockWorld()

    def test_breeds_with_adjacent_ready_mate(self):
        """Should return a BREED action if a suitable mate is adjacent."""
        mate = MockCritter(x=1, y=1, diet=DietType.HERBIVORE)
        all_critters = [self.critter, mate]

        behavior = MateSeekingBehavior()
        action = behavior.get_action(self.critter, self.world, all_critters)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.BREED)
        self.assertEqual(action["partner"], mate)

    def test_seeks_closest_ready_mate(self):
        """Should return a SEEK_MATE action for the closest suitable mate."""
        close_mate = MockCritter(x=3, y=3, diet=DietType.HERBIVORE)
        far_mate = MockCritter(x=5, y=5, diet=DietType.HERBIVORE)
        all_critters = [self.critter, far_mate, close_mate]

        behavior = MateSeekingBehavior()
        action = behavior.get_action(self.critter, self.world, all_critters)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        self.assertEqual(action["target"], (close_mate.x, close_mate.y))

    def test_ignores_mate_on_cooldown(self):
        """Should ignore potential mates that are on breeding cooldown."""
        mate_on_cooldown = MockCritter(x=1, y=1, diet=DietType.HERBIVORE, cooldown=100)
        all_critters = [self.critter, mate_on_cooldown]

        behavior = MateSeekingBehavior()
        action = behavior.get_action(self.critter, self.world, all_critters)
        self.assertIsNone(action)

    def test_ignores_mate_of_different_species(self):
        """Should ignore potential mates with a different diet."""
        carnivore_mate = MockCritter(x=1, y=1, diet=DietType.CARNIVORE)
        all_critters = [self.critter, carnivore_mate]

        behavior = MateSeekingBehavior()
        action = behavior.get_action(self.critter, None, all_critters)
        self.assertIsNone(action)
