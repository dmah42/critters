import argparse
import json
import logging
import os
import time
import traceback
from typing import Any, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from seasons import season_manager
from simulation.agent import DQNAgent
from simulation.engine import run_simulation_tick, training_group_size
from simulation.logger import setup_logging
from simulation.models import Critter, DietType, TrainingStats
from simulation.state_space import get_state_for_critter
from simulation.world import World


DEFAULT_HERBIVORE_MODEL_FILE: str = "herbivore.model.keras"
DEFAULT_CARNIVORE_MODEL_FILE: str = "carnivore.model.keras"
NUM_TRAINING_TICKS: int = 100000

logger = logging.getLogger(__name__)


def _get_sim_state(session: sessionmaker) -> Dict[str, Any]:
    """
    Queries the database for the most recent tick and epsilon values to enable
    clean restarting of the simulation.
    """
    db_session = session()
    latest_stats = db_session.query(TrainingStats).order_by(TrainingStats.tick.desc()).first()
    db_session.close()

    if latest_stats:
        return {
            "tick": latest_stats.tick,
            "herbivore_epsilon": latest_stats.herbivore_epsilon,
            "carnivore_epsilon": latest_stats.carnivore_epsilon,
        }
    else:
        # Default starting values if the database is empty
        return {"tick": 0, "herbivore_epsilon": 1.0, "carnivore_epsilon": 1.0}


def _create_agents(session_maker: sessionmaker, training: bool,
                   carnivore_model: str, herbivore_model: str) -> Dict[DietType, DQNAgent]:
    """Create an agent for each diet type"""
    session = session_maker()
    world = World(seed=Config.WORLD_SEED, session=session)

    all_critters = session.query(Critter).all()
    if not all_critters:
        logger.warning(
            "No living critters with which to initialize RL agents.")
        return {}

    sample_critter = all_critters[0]
    sample_state = get_state_for_critter(sample_critter, world, all_critters)
    state_size = len(sample_state)

    agents = {
        DietType.HERBIVORE: DQNAgent(herbivore_model, state_size, training=training, verbose=not training),
        DietType.CARNIVORE: DQNAgent(carnivore_model, state_size, training=training, verbose=not training),
    }
    logger.info("RL Agents Initialized.")

    session.close()

    return agents


def main():
    parser = argparse.ArgumentParser(description="Run Critter World sim loop")
    parser.add_argument(
        "-t",
        "--tick-timer",
        type=float,
        default=10.0,
        help="The time in seconds between sim ticks",
    )
    parser.add_argument(
        "--console-log",
        action="store_true",  # This makes it a boolean flag
        help="Enable logging to the console (logs will still go to the file).",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="simulation.log",
        help="The name of the file to save logs to.",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Run in high-speed training mode and save the weights.",
    )
    parser.add_argument("--training-group-size", type=int, default=32,
                        help="The number of critters to train each tick per diet.")
    parser.add_argument("--carnivore-model", type=str,
                        default=DEFAULT_CARNIVORE_MODEL_FILE,
                        help="File path for carnivore model")
    parser.add_argument("--herbivore-model", type=str,
                        default=DEFAULT_HERBIVORE_MODEL_FILE,
                        help="File path for herbivore model weights")
    args = parser.parse_args()

    global training_group_size
    training_group_size = args.training_group_size

    engine = create_engine(Config.SQLALCHEMY_SIM_DATABASE_URI)
    session_maker = sessionmaker(bind=engine)

    if args.train:
        setup_logging(console_log_enabled=False, log_filename=args.log_file)
    else:
        setup_logging(console_log_enabled=args.console_log,
                      log_filename=args.log_file)

    agents = _create_agents(session_maker,
                            args.train,
                            args.carnivore_model,
                            args.herbivore_model)

    if args.train:
        print(f"  Running simulation for {NUM_TRAINING_TICKS} ticks... ")
    else:
        print(f"Starting simulation loop with a {args.tick_timer}s tick... ")
    print("  Ctrl+C to exit.")

    sim_state = _get_sim_state(session_maker)

    tick: int = sim_state.get("tick", 0)

    if agents and args.train:
        agents[DietType.HERBIVORE].epsilon = sim_state.get(
            "herbivore_epsilon", 1.0)
        agents[DietType.CARNIVORE].epsilon = sim_state.get(
            "carnivore_epsilon", 1.0)

    try:
        while True:
            start_time = time.time()

            tick += 1

            if tick % 100 == 0:
                print(f"\n--- Saving weights at tick {tick} ---")
                agents[DietType.HERBIVORE].save()
                agents[DietType.CARNIVORE].save()

            if args.train and tick > NUM_TRAINING_TICKS:
                break

            session = session_maker()

            population_size = session.query(Critter).count()
            batch_size = args.training_group_size * 2  # Include both diet types

            if batch_size > 0 and population_size > 0:
                world_tick = int(tick * batch_size / population_size)
            else:
                world_tick = tick

            if args.train and tick % 10 == 0:
                print(f"\n--- Tick {tick} (World tick) {world_tick} ---")
                print(
                    f"Herbivore Epsilon: {agents[DietType.HERBIVORE].epsilon:.3f}")
                print(
                    f"Carnivore Epsilon: {agents[DietType.CARNIVORE].epsilon:.3f}")

            season_manager.update(world_tick)
            world = World(seed=Config.WORLD_SEED, session=session)

            try:
                run_simulation_tick(tick, world_tick, world, session, agents)
                session.commit()
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                logging.error(traceback.format_exc())
                traceback.print_exc()
                session.rollback()
                raise
            finally:
                session.close()

            end_time = time.time()

            # Skip the delay if we're training.
            if not args.train:
                time_taken = end_time - start_time
                sleep_time = args.tick_timer - time_taken

                if sleep_time > 0:
                    time.sleep(args.tick_timer)
                else:
                    logging.warning(
                        f"Tick processing ({time_taken:.2f}s) exceeded the "
                        f"tick timer duration ({args.tick_timer}s)"
                    )
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    finally:
        if args.train:
            agents[DietType.HERBIVORE].save()
            agents[DietType.CARNIVORE].save()


if __name__ == "__main__":
    main()
