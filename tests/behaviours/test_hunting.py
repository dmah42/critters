# tests/test_hunting.py

import unittest
import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.action_type import ActionType
from simulation.behaviours.hunting import HuntingBehavior
from simulation.models import DietType


class MockCritter:
    def __init__(self, x, y, diet, health=100.0, is_ghost=False):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y
        self.diet = diet
        self.health = health
        self.is_ghost = is_ghost
        self.perception = 8.0


class MockWorld:
    """A fake World that returns predictable terrain for testing."""

    def get_tile(self, x, y):
        # For this test, we'll just say there's food at (1, 1)
        has_food = 10.0 if x == 1 and y == 1 else 0.0
        return {
            "x": x,
            "y": y,
            "terrain": "grass",
            "food_available": has_food,
            "height": y,
        }


class TestHuntingBehavior(unittest.TestCase):

    def setUp(self):
        self.carnivore = MockCritter(x=0, y=0, diet=DietType.CARNIVORE)
        self.world = MockWorld()

    def test_ignores_ghost_prey(self):
        """
        Tests that a carnivore will ignore a nearby 'ghost' prey and
        target a living one further away.
        """
        # A very tempting, close-by prey, but it's a ghost
        ghost_prey = MockCritter(x=1, y=1, diet=DietType.HERBIVORE, is_ghost=True)
        # A healthy, living prey that is further away
        living_prey = MockCritter(x=4, y=4, diet=DietType.HERBIVORE, is_ghost=False)

        all_critters = [self.carnivore, ghost_prey, living_prey]

        behavior = HuntingBehavior()
        action = behavior.get_action(self.carnivore, self.world, all_critters)

        # Assert: The carnivore should ignore the ghost and target the living prey
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        self.assertEqual(action["target"], (living_prey.x, living_prey.y))

    def test_attacks_adjacent_prey_immediately(self):
        """A carnivore should always attack adjacent prey, regardless of other options."""
        adjacent_prey = MockCritter(x=1, y=0, diet=DietType.HERBIVORE, health=100.0)
        weaker_distant_prey = MockCritter(
            x=4, y=4, diet=DietType.HERBIVORE, health=20.0
        )
        all_critters = [self.carnivore, adjacent_prey, weaker_distant_prey]

        behavior = HuntingBehavior()
        action = behavior.get_action(self.carnivore, self.world, all_critters)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.ATTACK)
        self.assertEqual(action["target"], adjacent_prey)

    def test_hunts_weakest_prey_when_none_are_adjacent(self):
        """If no prey is adjacent, the carnivore should target the weakest one."""
        healthy_close_prey = MockCritter(
            x=2, y=2, diet=DietType.HERBIVORE, health=100.0
        )
        weak_far_prey = MockCritter(x=4, y=4, diet=DietType.HERBIVORE, health=20.0)
        all_critters = [self.carnivore, healthy_close_prey, weak_far_prey]

        behavior = HuntingBehavior()
        action = behavior.get_action(self.carnivore, self.world, all_critters)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        self.assertEqual(action["target"], (weak_far_prey.x, weak_far_prey.y))

    def test_hunts_closest_prey_when_health_is_equal(self):
        """If multiple prey have the same health, it should target the closest one."""
        close_prey = MockCritter(x=2, y=2, diet=DietType.HERBIVORE, health=50.0)
        far_prey = MockCritter(x=4, y=4, diet=DietType.HERBIVORE, health=50.0)
        all_critters = [self.carnivore, far_prey, close_prey]

        behavior = HuntingBehavior()
        action = behavior.get_action(self.carnivore, self.world, all_critters)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        self.assertEqual(action["target"], (close_prey.x, close_prey.y))

    def test_returns_none_if_no_prey_in_range(self):
        """If there are no herbivores in sensing range, it should return None."""
        all_critters = [self.carnivore]
        behavior = HuntingBehavior()
        action = behavior.get_action(self.carnivore, self.world, all_critters)
        self.assertIsNone(action)
