from typing import List
import numpy as np

from .models import Critter, DietType, TerrainType
from .world import World
from simulation.brain import (
    CARNIVORE_MIN_ENERGY_TO_BREED,
    HERBIVORE_MIN_ENERGY_TO_BREED,
    MAX_HUNGER_TO_BREED,
    MAX_THIRST_TO_BREED,
    MIN_HEALTH_TO_BREED,
    SENSE_RADIUS,
)

def get_state_for_critter(critter: Critter, world: World, all_critters: List[Critter]) -> np.ndarray:
    """
    Gathers all sensory input for a critter into a single numpy array (vector).
    This vector represents the complete "state" for the RL agent.
    """
    # --- 1. Internal State ---
    # A vector of the critter's own vital stats, normalized to be roughly between 0 and 1.
    internal_state = np.array([
        critter.health / critter.max_health,
        critter.energy / 100.0,
        critter.hunger / 100.0,
        critter.thirst / 100.0,
        critter.age / (critter.lifespan + 1),  # Avoid division by zero
        critter.breeding_cooldown / 500.0,
    ], dtype=np.float32)

    # --- 2. External State (What the critter sees) ---
    # We create "layers" of perception for the surrounding area.
    # The size of the grid is based on the critter's perception.
    local_dim = (SENSE_RADIUS * 2) + 1

    # Layer 1: Terrain Height
    height_map = np.zeros((local_dim, local_dim), dtype=np.float32)
    # Layer 2: Food Availability
    food_map = np.zeros((local_dim, local_dim), dtype=np.float32)
    # Layer 3: Presence of other critters (friend or foe)
    critter_map = np.zeros((local_dim, local_dim), dtype=np.float32)

    for y_offset in range(-SENSE_RADIUS, SENSE_RADIUS + 1):
        for x_offset in range(-SENSE_RADIUS, SENSE_RADIUS + 1):
            # Convert world offset to array index
            array_y = y_offset + SENSE_RADIUS
            array_x = x_offset + SENSE_RADIUS

            # Get tile data from the world
            wx, wy = critter.x + x_offset, critter.y + y_offset
            tile = world.get_tile(wx, wy)

            height_map[array_y, array_x] = tile.height
            if tile.terrain == TerrainType.GRASS:
                food_map[array_y, array_x] = tile.food_available / 10.0

    visible_critters = [
        other for other in all_critters if other.id != critter.id and
        abs(other.x - critter.x) <= critter.perception and
        abs(other.y - critter.y) <= critter.perception
    ]

    # Initialize summary vectors
    closest_predator_vec = np.zeros(3, dtype=np.float32)  # [distance, dx, dy]
    # [distance, dx, dy, health]
    weakest_prey_vec = np.zeros(4, dtype=np.float32)
    closest_mate_vec = np.zeros(3, dtype=np.float32)

    if critter.diet == DietType.HERBIVORE:
        predators = [c for c in visible_critters if c.diet ==
                     DietType.CARNIVORE]
        if predators:
            closest = min(predators, key=lambda p: abs(
                p.x-critter.x) + abs(p.y-critter.y))
            dist = (abs(closest.x - critter.x) +
                    abs(closest.y - critter.y)) / critter.perception
            dx = (closest.x - critter.x) / critter.perception
            dy = (closest.y - critter.y) / critter.perception
            closest_predator_vec = np.array([dist, dx, dy], dtype=np.float32)

    elif critter.diet == DietType.CARNIVORE:
        prey = [c for c in visible_critters if c.diet == DietType.HERBIVORE]
        if prey:
            # Find the weakest, then closest prey (our vulnerability logic)
            prey.sort(key=lambda p: (p.health, abs(
                p.x-critter.x) + abs(p.y-critter.y)))
            weakest = prey[0]
            dist = (abs(weakest.x - critter.x) +
                    abs(weakest.y - critter.y)) / critter.perception
            dx = (weakest.x - critter.x) / critter.perception
            dy = (weakest.y - critter.y) / critter.perception
            health = weakest.health / weakest.max_health
            weakest_prey_vec = np.array(
                [dist, dx, dy, health], dtype=np.float32)


    is_ready_to_breed = (
        critter.health >= MIN_HEALTH_TO_BREED and
        critter.hunger < MAX_HUNGER_TO_BREED and
        critter.thirst < MAX_THIRST_TO_BREED and
        critter.energy >= (CARNIVORE_MIN_ENERGY_TO_BREED if critter.diet == DietType.CARNIVORE else HERBIVORE_MIN_ENERGY_TO_BREED) and
        critter.breeding_cooldown == 0
    )

    if is_ready_to_breed:
        potential_mates = [
            other for other in visible_critters
            if other.diet == critter.diet
            and other.health >= MIN_HEALTH_TO_BREED
            and other.hunger < MAX_HUNGER_TO_BREED
            and other.thirst < MAX_THIRST_TO_BREED
            and other.energy >= (CARNIVORE_MIN_ENERGY_TO_BREED if critter.diet == DietType.CARNIVORE else HERBIVORE_MIN_ENERGY_TO_BREED)
            and other.breeding_cooldown == 0
        ]

        if potential_mates:
            closest = min(potential_mates, key=lambda m: abs(m.x-critter.x) + abs(m.y-critter.y))
            dist = (abs(closest.x - critter.x) + abs(closest.y - critter.y)) / critter.perception
            dx = (closest.x - critter.x) / critter.perception
            dy = (closest.y - critter.y) / critter.perception
            closest_mate_vec = np.array([dist, dx, dy], dtype=np.float32)

    # --- 3. Combine and Flatten ---
    # We flatten the 2D perception maps into 1D vectors and concatenate everything.
    final_state = np.concatenate([
        internal_state,
        height_map.flatten(),
        food_map.flatten(),
        closest_predator_vec,
        weakest_prey_vec,
        closest_mate_vec,
    ])

    return final_state
