import argparse
import logging
import time
import traceback
from typing import Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from simulation.agent import DQNAgent
from simulation.engine import run_simulation_tick
from simulation.logger import setup_logging
from simulation.models import Critter, DietType
from simulation.state_space import get_state_for_critter
from simulation.world import World


logger = logging.getLogger(__name__)


def _create_agents(session_maker: sessionmaker) -> Dict[DietType, DQNAgent]:
    """Create an agent for each diet type"""
    session = session_maker()
    world = World(seed=Config.WORLD_SEED, session=session)

    all_critters = session.query(Critter).all()
    if not all_critters:
        logger.warning(
            "No living critters with which to initialize RL agents.")
        return {}

    sample_state = get_state_for_critter(all_critters[0], world, all_critters)
    state_size = len(sample_state)

    agents = {
        DietType.HERBIVORE: DQNAgent(state_size, verbose=True),
        DietType.CARNIVORE: DQNAgent(state_size, verbose=True),
    }
    logger.info("RL Agents Initialized.")

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
    args = parser.parse_args()

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    session_maker = sessionmaker(bind=engine)

    setup_logging(console_log_enabled=args.console_log, log_filename=args.log_file)

    agents = _create_agents(session_maker)

    print(f"Starting simulation loop with a {args.tick_timer}s tick... ")
    print("  Ctrl+C to exit.")

    tick: int = 0
    while True:
        start_time = time.time()

        tick += 1
        if tick % 100 == 0:
            print(f"\n--- Tick {tick} ---")
            print(
                f"Herbivore Epsilon: {agents[DietType.HERBIVORE].epsilon:.3f}")
            print(
                f"Carnivore Epsilon: {agents[DietType.CARNIVORE].epsilon:.3f}")

        session = session_maker()
        world = World(seed=Config.WORLD_SEED, session=session)

        try:
            run_simulation_tick(world, session, agents)
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

        time_taken = end_time - start_time
        sleep_time = args.tick_timer - time_taken

        if sleep_time > 0:
            time.sleep(args.tick_timer)
        else:
            logging.warning(
                f"Tick processing ({time_taken:.2f}s) exceeded the "
                f"tick timer duration ({args.tick_timer}s)"
            )


if __name__ == "__main__":
    main()
