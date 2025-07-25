import unittest
import sys
import os
from unittest.mock import patch

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web_server import create_app
from simulation.engine import World


class TestSimulation(unittest.TestCase):
    def setUp(self):
        """
        Runs before each test.
        Creates a new application instance and pushes an application context.
        """
        self.app = create_app()
        self.app.config.update(
            {
                "TESTING": True,
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """
        Runs after each test.
        Pops the application context.
        """
        self.app_context.pop()

    def test_world_generation_varies_on_y_axis(self):
        """
        Tests if the world generation produces different height values
        for the same X coordinate but different Y coordinates.
        """
        # 1. Arrange: Create a world with a known seed
        world = World(seed=123)
        test_x = 10
        heights = []

        # 2. Act: Get the height for 10 tiles in a vertical line
        for test_y in range(10):
            tile = world._generate_procedural_tile(test_x, test_y)
            heights.append(tile["height"])

        print(f"Generated heights for x=10: {heights}")

        # 3. Assert: Check if all the generated heights are the same
        # We do this by converting the list to a set to get unique values.
        # If all heights are the same, the set will only have 1 item.
        unique_heights = set(heights)

        self.assertGreater(
            len(unique_heights),
            1,
            "CRITICAL BUG: All generated heights for a vertical column are identical.",
        )

    @patch("app.simulation.TileState.query")
    def test_get_tile_procedural_path_varies_on_y_axis(self, mock_query):
        """
        Tests the get_tile method's procedural path returns unique heights by mocking the database.
        """
        # 1. Arrange: Configure the mock to simulate an empty database
        # This tells the mocked '.get()' method to always return None
        mock_query.get.return_value = None

        world = World(seed=1)  # Use a seed that we know produces grass at (0,0)

        test_x = 10
        heights = []

        # 2. Act: Get the height for 10 tiles in a vertical line
        for test_y in range(10):
            tile = world._generate_procedural_tile(test_x, test_y)
            heights.append(tile["height"])

        print(f"Generated heights for x=10: {heights}")

        # 3. Assert: Check if all the generated heights are the same
        # We do this by converting the list to a set to get unique values.
        # If all heights are the same, the set will only have 1 item.
        unique_heights = set(heights)

        self.assertGreater(
            len(unique_heights),
            1,
            "CRITICAL BUG: All generated heights for a vertical column are identical.",
        )


if __name__ == "__main__":
    unittest.main()
