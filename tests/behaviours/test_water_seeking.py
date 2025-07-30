# tests/test_water_seeking.py

import unittest
import sys
import os
import random

from simulation.action_type import ActionType
from simulation.behaviours.water_seeking import WaterSeekingBehavior
from simulation.terrain_type import TerrainType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class MockCritter:
    def __init__(self, x, y):
        self.id = random.randint(1, 1000)
        self.x = x
        self.y = y


class MockWorld:
    def __init__(self, water_locations):
        self.water_locations = set(water_locations)

    def get_tile(self, x, y):
        terrain = (
            TerrainType.WATER if (x, y) in self.water_locations else TerrainType.GRASS
        )
        return {"x": x, "y": y, "terrain": terrain}


class TestWaterSeekingBehavior(unittest.TestCase):

    def test_drinks_when_adjacent_to_water(self):
        """Should return a DRINK action if the critter is next to water."""
        critter = MockCritter(x=0, y=0)
        world = MockWorld(water_locations=[(1, 0)])

        behavior = WaterSeekingBehavior()
        action = behavior.get_action(critter, world)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.DRINK)

    def test_seeks_closest_shore_tile(self):
        """Should target the closest land tile adjacent to the nearest water."""
        critter = MockCritter(x=0, y=0)
        # Water is at (5,5), so the closest shore tile is (4,5) or (5,4)
        world = MockWorld(water_locations=[(5, 5)])

        behavior = WaterSeekingBehavior()
        action = behavior.get_action(critter, world)

        self.assertIsNotNone(action)
        self.assertEqual(action["type"], ActionType.MOVE)
        # The target should be a land tile next to the water
        self.assertIn(action["target"], [(4, 5), (5, 4), (4, 4)])

    def test_returns_none_if_no_water_in_range(self):
        """Should return None if there is no water in the sensing radius."""
        critter = MockCritter(x=0, y=0)
        world = MockWorld(water_locations=[(100, 100)])  # Water is very far away

        behavior = WaterSeekingBehavior()
        action = behavior.get_action(critter, world)
        self.assertIsNone(action)
