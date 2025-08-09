import unittest
import sys
import os
import random
from unittest.mock import patch

from simulation.terrain_type import TerrainType

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.brain import ENERGY_TO_START_RESTING, HUNGER_TO_START_FORAGING
from simulation.models import (
    Critter,
    CritterEvent,
    DeadCritter,
    DietType,
    AIState,
    CauseOfDeath,
)
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
        self.max_health = health
        self.energy = energy
        self.hunger = hunger
        self.thirst = thirst
        self.movement_progress = 0.0
        self.age = age
        self.speed = speed
        self.size = size
        self.metabolism = 1.0
        self.lifespan = 100.0
        self.perception = 5.0
        self.commitment = 1.25
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
    """A simple spy that records calls made to it."""

    def __init__(self):
        self.added = []
        self.deleted = []
        self.flushed = False

    def query(self, _):
        pass

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def flush(self):
        self.flushed = True


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

    @patch("simulation.engine._update_tile_food")
    def test_critter_eats_when_hungry_on_food(self, mock_update_food):
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

    def test_handle_death_adds_and_deletes(self):
        """
        Tests that _handle_death adds a DeadCritter and deletes a Critter,
        without flushing.
        """
        session = MockSession()
        critter_to_die = MockCritter(id=123)

        # Act
        _handle_death(critter_to_die, CauseOfDeath.STARVATION, session)

        # Assert
        self.assertEqual(len(session.added), 2)
        added_types = [type(obj) for obj in session.added]
        self.assertIn(DeadCritter, added_types)
        self.assertIn(CritterEvent, added_types)

        self.assertEqual(len(session.deleted), 1)
        self.assertIs(session.deleted[0], critter_to_die)

        self.assertFalse(session.flushed)  # Crucially, it should NOT flush

    def test_reproduce_adds_and_flushes(self):
        """
        Tests that _reproduce adds a new Critter and then flushes the session.
        """
        session = MockSession()
        parent1 = MockCritter(id=1)
        parent2 = MockCritter(id=2)

        # Act
        _reproduce(parent1, parent2, session)

        # Assert
        self.assertEqual(len(session.added), 4)
        added_types = [type(obj) for obj in session.added]
        self.assertIn(Critter, added_types)
        self.assertIn(CritterEvent, added_types)

        self.assertTrue(session.flushed)  # Crucially, it SHOULD flush

    def test_handle_death_fails_for_ghost(self):
        with self.assertRaises(RuntimeError):
            critter_to_die = MockCritter(id=123, age=100, is_ghost=True)
            _handle_death(critter_to_die, CauseOfDeath.STARVATION, self.session)
