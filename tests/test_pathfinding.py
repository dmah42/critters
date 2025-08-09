# tests/test_pathfinding.py

import unittest
import sys
import os

from simulation.terrain_type import TerrainType
from simulation.world import TileData

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.pathfinding import find_path


class MockWorld:
    """A mock world that can be configured with obstacles and heights."""

    def __init__(self, obstacles=None, heights=None):
        self.obstacles = obstacles if obstacles is not None else set()
        self.heights = heights if heights is not None else {}

    def get_tile(self, x, y) -> TileData:
        terrain = TerrainType.WATER if (x, y) in self.obstacles else TerrainType.GRASS
        height = self.heights.get((x, y), 0.0)  # Default to flat ground
        return TileData(x=x, y=y, terrain=terrain, height=height, food_available=1.0)


class TestPathfinding(unittest.TestCase):

    def test_finds_simple_path(self):
        """Tests that the A* algorithm can find a direct path on an open plane."""
        world = MockWorld()
        start = (0, 0)
        end = (3, 3)
        path = find_path(world, start, end)

        self.assertIsNotNone(path)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], end)
        self.assertEqual(len(path), 4)  # (0,0)->(1,1)->(2,2)->(3,3) is 4 steps

    def test_paths_around_obstacles(self):
        """Tests that the A* algorithm correctly navigates around a wall."""
        # Create a vertical wall of water
        obstacles = {(1, 0), (1, 1), (1, 2), (1, 3)}
        world = MockWorld(obstacles=obstacles)
        start = (0, 1)
        end = (2, 1)
        path = find_path(world, start, end)

        self.assertIsNotNone(path)
        self.assertNotIn((1, 1), path)  # Ensure it didn't go through the wall
        self.assertEqual(path[-1], end)

    def test_finds_cheapest_energy_path(self):
        """
        Tests that the A* algorithm chooses a longer, flat path over a
        shorter, high-energy mountain path.
        """
        # A "mountain" at (1,0) has a very high elevation
        heights = {(1, 0): 10.0}
        world = MockWorld(heights=heights)
        start = (0, 0)
        end = (2, 0)

        # The shortest path is (0,0) -> (1,0) -> (2,0), but it's very expensive.
        # The cheapest path is to go around the mountain, e.g., (0,0)->(0,1)->(1,1)->(2,1)->(2,0)

        path = find_path(world, start, end)

        self.assertIsNotNone(path)
        # Check that the path avoids the expensive mountain tile
        self.assertNotIn((1, 0), path)
        self.assertEqual(path[-1], end)

    def test_a_star_chooses_smarter_path_over_longer_one(self):
        """
        Tests that A* correctly uses the f_cost to choose a path that is
        overall shorter, even if the first step seems longer.
        """
        # SCENARIO: A critter at (0,0) wants to get to (1,5).
        # Path A (dumb): Go straight up to (0,5) and then right to (1,5). Total steps: 6.
        # Path B (smart): Go diagonally up-right to (1,1), then straight up. Total steps: 5.
        # A correct A* will immediately see that the diagonal path is more promising.

        world = MockWorld()
        start = (0, 0)
        end = (1, 5)

        path = find_path(world, start, end)

        self.assertIsNotNone(path)
        self.assertEqual(
            len(path), 6
        )  # The path is (0,0)->(1,1)->(1,2)->(1,3)->(1,4)->(1,5)

        # The most important check: The second step in the path MUST be (1,1).
        # This proves the algorithm correctly chose the diagonal step first.
        self.assertEqual(path[1], (1, 1))
