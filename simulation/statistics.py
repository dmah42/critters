import json
import logging
import math
from typing import Dict
import numpy as np

from simulation.agent import DQNAgent
from simulation.models import Critter, DietType, SimulationStats, TrainingStats
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_percentiles(critter_list, trait_name):
    if not critter_list:
        return None, None, None
    values = [getattr(c, trait_name) for c in critter_list]
    q1, median, q3 = np.percentile(values, [25, 50, 75])
    return q1, median, q3


def record_statistics(session: Session):
    """Calculates and saves the current sim stats"""
    critters = session.query(Critter).all()
    population = len(critters)

    if population == 0:
        logger.warning("No living critters")
        return

    herbivore_stats = {
        "count": 0,
        "ages": {},
        "health": {"Healthy": 0, "Hurt": 0, "Critical": 0},
        "hunger": {},
        "thirst": {},
        "energy": {},
    }
    carnivore_stats = {
        "count": 0,
        "ages": {},
        "health": {"Healthy": 0, "Hurt": 0, "Critical": 0},
        "hunger": {},
        "thirst": {},
        "energy": {},
    }

    goal_bins = {}

    for c in critters:
        stats_dict = (
            herbivore_stats if c.diet == DietType.HERBIVORE else carnivore_stats
        )

        stats_dict["count"] += 1

        stats_dict["ages"][c.age] = stats_dict["ages"].get(c.age, 0) + 1
        hunger_bin = int(math.floor(c.hunger))
        stats_dict["hunger"][hunger_bin] = stats_dict["hunger"].get(
            hunger_bin, 0) + 1
        thirst_bin = int(math.floor(c.thirst))
        stats_dict["thirst"][thirst_bin] = stats_dict["thirst"].get(
            thirst_bin, 0) + 1
        energy_bin = int(math.floor(c.energy))
        stats_dict["energy"][energy_bin] = stats_dict["energy"].get(
            energy_bin, 0) + 1

        if c.health > 70:
            stats_dict["health"]["Healthy"] += 1
        elif c.health > 30:
            stats_dict["health"]["Hurt"] += 1
        else:
            stats_dict["health"]["Critical"] += 1

        goal_bin = c.ai_state.name
        goal_bins[goal_bin] = goal_bins.get(goal_bin, 0) + 1

    herbivores = [c for c in critters if c.diet == DietType.HERBIVORE]
    carnivores = [c for c in critters if c.diet == DietType.CARNIVORE]

    # Calculate genetic distributions for herbivores
    h_speed_q1, h_speed_med, h_speed_q3 = _get_percentiles(herbivores, "speed")
    h_size_q1, h_size_med, h_size_q3 = _get_percentiles(herbivores, "size")
    h_metabolism_q1, h_metabolism_med, h_metabolism_q3 = _get_percentiles(
        herbivores, "metabolism"
    )
    h_commitment_q1, h_commitment_med, h_commitment_q3 = _get_percentiles(
        herbivores, "commitment"
    )
    h_perception_q1, h_perception_med, h_perception_q3 = _get_percentiles(
        herbivores, "perception"
    )

    # Calculate genetic distributions for carnivores
    c_speed_q1, c_speed_med, c_speed_q3 = _get_percentiles(carnivores, "speed")
    c_size_q1, c_size_med, c_size_q3 = _get_percentiles(carnivores, "size")
    c_metabolism_q1, c_metabolism_med, c_metabolism_q3 = _get_percentiles(
        carnivores, "metabolism"
    )
    c_commitment_q1, c_commitment_med, c_commitment_q3 = _get_percentiles(
        carnivores, "commitment"
    )
    c_perception_q1, c_perception_med, c_perception_q3 = _get_percentiles(
        carnivores, "perception"
    )

    last_stat = (
        session.query(SimulationStats).order_by(
            SimulationStats.tick.desc()).first()
    )
    current_tick = (last_stat.tick + 1) if last_stat else 1

    stats = SimulationStats(
        tick=current_tick,
        population=population,
        herbivore_population=herbivore_stats["count"],
        carnivore_population=carnivore_stats["count"],
        herbivore_age_distribution=json.dumps(herbivore_stats["ages"]),
        carnivore_age_distribution=json.dumps(carnivore_stats["ages"]),
        herbivore_health_distribution=json.dumps(herbivore_stats["health"]),
        carnivore_health_distribution=json.dumps(carnivore_stats["health"]),
        herbivore_hunger_distribution=json.dumps(herbivore_stats["hunger"]),
        carnivore_hunger_distribution=json.dumps(carnivore_stats["hunger"]),
        herbivore_thirst_distribution=json.dumps(herbivore_stats["thirst"]),
        carnivore_thirst_distribution=json.dumps(carnivore_stats["thirst"]),
        herbivore_energy_distribution=json.dumps(herbivore_stats["energy"]),
        carnivore_energy_distribution=json.dumps(carnivore_stats["energy"]),
        goal_distribution=json.dumps(goal_bins),
        herbivore_speed_q1=h_speed_q1,
        herbivore_speed_median=h_speed_med,
        herbivore_speed_q3=h_speed_q3,
        carnivore_speed_q1=c_speed_q1,
        carnivore_speed_median=c_speed_med,
        carnivore_speed_q3=c_speed_q3,
        herbivore_size_q1=h_size_q1,
        herbivore_size_median=h_size_med,
        herbivore_size_q3=h_size_q3,
        carnivore_size_q1=c_size_q1,
        carnivore_size_median=c_size_med,
        carnivore_size_q3=c_size_q3,
        herbivore_metabolism_q1=h_metabolism_q1,
        herbivore_metabolism_median=h_metabolism_med,
        herbivore_metabolism_q3=h_metabolism_q3,
        carnivore_metabolism_q1=c_metabolism_q1,
        carnivore_metabolism_median=c_metabolism_med,
        carnivore_metabolism_q3=c_metabolism_q3,
        herbivore_commitment_q1=h_commitment_q1,
        herbivore_commitment_median=h_commitment_med,
        herbivore_commitment_q3=h_commitment_q3,
        carnivore_commitment_q1=c_commitment_q1,
        carnivore_commitment_median=c_commitment_med,
        carnivore_commitment_q3=c_commitment_q3,
        herbivore_perception_q1=h_perception_q1,
        herbivore_perception_median=h_perception_med,
        herbivore_perception_q3=h_perception_q3,
        carnivore_perception_q1=c_perception_q1,
        carnivore_perception_median=c_perception_med,
        carnivore_perception_q3=c_perception_q3,
    )
    session.add(stats)

    logger.info(f"  Recorded stats for tick {current_tick}: {stats.to_dict()}")


def record_training_statistics(
    session: Session,
    agents: Dict[DietType, DQNAgent],
    avg_rewards: Dict[DietType, float],
):
    """Records a snapshot of the training-specific statistics to the database."""
    last_stat = (
        session.query(TrainingStats).order_by(
            TrainingStats.tick.desc()).first()
    )
    current_tick = (last_stat.tick + 1) if last_stat else 1
    new_training_stats = TrainingStats(
        tick=current_tick,
        herbivore_epsilon=agents[DietType.HERBIVORE].epsilon,
        carnivore_epsilon=agents[DietType.CARNIVORE].epsilon,
        avg_reward_herbivore=avg_rewards.get(DietType.HERBIVORE, 0),
        avg_reward_carnivore=avg_rewards.get(DietType.CARNIVORE, 0),
    )
    session.add(new_training_stats)
