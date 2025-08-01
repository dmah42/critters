import unittest
import sys
import os
import random

from simulation.terrain_type import TerrainType

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.brain import ENERGY_TO_START_RESTING, HUNGER_TO_START_FORAGING
from simulation.models import DietType, AIState, CauseOfDeath
from simulation.engine import (
    DEFAULT_GRASS_FOOD,
    _run_critter_logic,
    _handle_death,
    _reproduce,
)

# --- Mock Objects for Testing the Engine ---


class MockCritter:
    """A fake Critter for testing engine logic."""

    def __init__(
        self,
        id=None,
        x=0,
        y=0,
        vx=0,
        vy=0,
        diet=DietType.HERBIVORE,
        health=100.0,
        energy=100.0,
        hunger=0.0,
        thirst=0.0,
        age=1,
        speed=5.0,
        size=5.0,
        ai_state=AIState.IDLE,
        breeding_cooldown=0,
        parent_one_id=0,
        parent_two_id=0,
        is_ghost=False,
    ):
        self.id = id if id is not None else random.randint(1, 1000)
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.diet = diet
        self.health = health
        self.energy = energy
        self.hunger = hunger
        self.thirst = thirst
        self.movement_progress = 0.0
        self.age = age
        self.speed = speed
        self.size = size
        self.metabolism = 1.0
        self.ai_state = ai_state
        self.breeding_cooldown = breeding_cooldown
        self.parent_one_id = parent_one_id
        self.parent_two_id = parent_two_id
        # Add a placeholder for player_id
        self.player_id = None
        self.is_ghost = is_ghost


class MockWorld:
    """A fake World that returns predictable terrain for testing."""

    def __init__(self, tile_state_overrides=None):
        self.tile_state_overrides = (
            tile_state_overrides if tile_state_overrides is not None else {}
        )

    def get_tile(self, x, y):
        food_amount = DEFAULT_GRASS_FOOD
        if (x, y) in self.tile_state_overrides:
            food_amount = self.tile_state_overrides.get((x, y), 0.0)

        terrain = TerrainType.GRASS if food_amount > 0 else TerrainType.DIRT
        if y > 5:  # Let's add some water for testing
            terrain = TerrainType.WATER

        return {
            "x": x,
            "y": y,
            "terrain": terrain,
            "food_available": food_amount,
            "height": y,
        }


class MockQuery:
    """A fake query object that simulates the .get() method."""

    def __init__(self, items):
        self._items = {item.id: item for item in items if hasattr(item, "id")}
        self._tile_items = {
            (item.x, item.y): item for item in items if hasattr(item, "x")
        }

    def get(self, ident):
        # This can now handle both integer IDs and (x, y) tuples
        return self._items.get(ident) or self._tile_items.get(ident)


class MockSession:
    """A fake database session that can simulate a simple query."""

    def __init__(self, initial_objects=None):
        self.new = []
        self.deleted = set()
        self._initial_objects = initial_objects if initial_objects is not None else []

    def query(self, model_class):
        # This method now returns our fake query object
        return MockQuery(self._initial_objects)

    def add(self, obj):
        self.new.append(obj)

    def delete(self, obj):
        self.deleted.add(obj)


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.world = MockWorld()
        self.session = MockSession()

    def test_critter_rests_when_tired(self):
        """Tests that an exhausted critter's only action is to rest."""
        # Use the mock to create a critter in the exact state we need
        tired_critter = MockCritter(energy=ENERGY_TO_START_RESTING - 1)

        _run_critter_logic(
            tired_critter,
            self.world,
            self.session,
            [tired_critter],
        )

        self.assertGreater(tired_critter.energy, ENERGY_TO_START_RESTING - 1)
        self.assertEqual(tired_critter.ai_state, AIState.RESTING)

    def test_critter_eats_when_hungry_on_food(self):
        """Tests that a hungry critter on a food tile will eat."""
        hungry_critter = MockCritter(hunger=HUNGER_TO_START_FORAGING + 1)
        world_with_food = MockWorld(tile_state_overrides={(0, 0): 10.0})

        _run_critter_logic(
            hungry_critter,
            world_with_food,
            self.session,
            [hungry_critter],
        )

        self.assertLess(hungry_critter.hunger, HUNGER_TO_START_FORAGING + 1)
        self.assertEqual(hungry_critter.ai_state, AIState.EATING)

    def test_handle_death_creates_dead_critter(self):
        """Tests that the death handler correctly archives a critter."""
        critter_to_die = MockCritter(id=123, age=100)

        _handle_death(critter_to_die, CauseOfDeath.STARVATION, self.session)

        self.assertEqual(len(self.session.new), 1)
        self.assertEqual(self.session.new[0].original_id, 123)
        self.assertIn(critter_to_die, self.session.deleted)

    def test_handle_death_fails_for_ghost(self):
        with self.assertRaises(RuntimeError):
            critter_to_die = MockCritter(id=123, age=100, is_ghost=True)
            _handle_death(critter_to_die, CauseOfDeath.STARVATION, self.session)

    def test_reproduce_creates_child(self):
        """Tests that reproduction creates a new critter."""
        parent1 = MockCritter(id=1, speed=5.0, size=5.0, diet=DietType.HERBIVORE)
        parent2 = MockCritter(id=2, speed=4.0, size=6.0, diet=DietType.HERBIVORE)

        _reproduce(parent1, parent2, self.session)

        self.assertEqual(len(self.session.new), 1)
        # We need to import the real Critter model to check the type
        from simulation.models import Critter

        self.assertIsInstance(self.session.new[0], Critter)
        self.assertEqual(self.session.new[0].parent_one_id, 1)
        self.assertGreaterEqual(self.session.new[0].speed, 3.8)
        self.assertLessEqual(self.session.new[0].speed, 5.2)
        self.assertGreaterEqual(self.session.new[0].size, 4.8)
        self.assertLessEqual(self.session.new[0].size, 6.2)
