import math
from typing import List

import numpy as np

from simulation.brain import MAX_ENERGY, SENSE_RADIUS
from simulation.models import Critter, DietType
from simulation.terrain_type import TerrainType
from simulation.world import World


def get_state_for_critter(critter: Critter, world: World, all_critters: List[Critter]) -> np.ndarray:
    """
    Gathers all sensory input for a critter into a single numpy array (vector).
    This vector represents the complete "state" for the RL agent.
    """
    # --- 1. Internal State ---
    # A vector of the critter's own vital stats, normalized to be roughly between 0 and 1.
    internal_state = np.array([
        float(critter.diet == DietType.CARNIVORE),  # 1 if carnivore, 0 if herbivore
        critter.health / critter.max_health,
        critter.energy / 100.0,
        critter.hunger / 100.0,
        critter.thirst / 100.0,
        critter.age / (critter.lifespan + 1),
        critter.breeding_cooldown / 500.0,
        critter.perception / 10.0,
    ], dtype=np.float32)

    # --- 2. External State (What the critter sees) ---
    local_dim = int((SENSE_RADIUS * 2) + 1)
    height_map = np.zeros((local_dim, local_dim), dtype=np.float32)
    grass_map = np.zeros((local_dim, local_dim), dtype=np.float32)
    water_map = np.zeros((local_dim, local_dim), dtype=np.float32)

    for y_offset in range(-SENSE_RADIUS, SENSE_RADIUS + 1):
        for x_offset in range(-SENSE_RADIUS, SENSE_RADIUS + 1):
            array_y, array_x = y_offset + SENSE_RADIUS, x_offset + SENSE_RADIUS
            wx, wy = critter.x + x_offset, critter.y + y_offset
            tile = world.get_tile(wx, wy)
            height_map[array_y, array_x] = tile.height
            if tile.terrain == TerrainType.GRASS:
                grass_map[array_y, array_x] = tile.food_available / 10.0
            elif tile.terrain == TerrainType.WATER:
                water_map[array_y, array_x] = 1.0

    perception = math.ceil(critter.perception)
    # --- Information about other critters ---
    visible_critters = [
        other for other in all_critters
        if other.id != critter.id and
        abs(other.x - critter.x) <= perception and
        abs(other.y - critter.y) <= perception
    ]

    # Closest Predator Vector (distance, dx, dy, health, energy) - for herbivores
    closest_predator_vec = np.zeros(5, dtype=np.float32)
    if critter.diet == DietType.HERBIVORE:
        visible_predators = [p for p in visible_critters if p.diet == DietType.CARNIVORE]
        if visible_predators:
            closest_predator = min(visible_predators, key=lambda p: abs(p.x - critter.x) + abs(p.y - critter.y))
            dist = (abs(closest_predator.x - critter.x) + abs(closest_predator.y - critter.y)) / perception
            dx = (closest_predator.x - critter.x) / perception
            dy = (closest_predator.y - critter.y) / perception
            health = closest_predator.health / closest_predator.max_health
            energy = closest_predator.energy / MAX_ENERGY
            closest_predator_vec = np.array([dist, dx, dy, health, energy], dtype=np.float32)

    # Weakest Prey Vector (distance, dx, dy, health, energy) - for carnivores
    weakest_prey_vec = np.zeros(5, dtype=np.float32)
    if critter.diet == DietType.CARNIVORE:
        visible_prey = [p for p in visible_critters if p.diet == DietType.HERBIVORE]
        if visible_prey:
            # Find prey with the lowest health, as it's the "weakest"
            weakest_prey = min(visible_prey, key=lambda p: p.health)
            dist = (abs(weakest_prey.x - critter.x) + abs(weakest_prey.y - critter.y)) / perception
            dx = (weakest_prey.x - critter.x) / perception
            dy = (weakest_prey.y - critter.y) / perception
            health = weakest_prey.health / weakest_prey.max_health
            energy = weakest_prey.energy / MAX_ENERGY
            weakest_prey_vec = np.array([dist, dx, dy, health, energy], dtype=np.float32)

    # Closest Mate Vector (distance, dx, dy)
    closest_mate_vec = np.zeros(3, dtype=np.float32)
    if critter.breeding_cooldown == 0:
        potential_mates = [
            m for m in visible_critters
            if m.diet == critter.diet and m.breeding_cooldown == 0
        ]
        if potential_mates:
            closest_mate = min(potential_mates, key=lambda m: abs(m.x-critter.x) + abs(m.y-critter.y))
            dist = (abs(closest_mate.x - critter.x) + abs(closest_mate.y - critter.y)) / perception
            dx = (closest_mate.x - critter.x) / perception
            dy = (closest_mate.y - critter.y) / perception
            closest_mate_vec = np.array([dist, dx, dy], dtype=np.float32)


    # --- 3. Combine and Flatten ---
    final_state = np.concatenate([
        internal_state,
        height_map.flatten(),
        grass_map.flatten(),
        water_map.flatten(),
        closest_predator_vec,
        weakest_prey_vec,
        closest_mate_vec,
    ])

    return final_state
