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


DEFAULT_HERBIVORE_WEIGHTS_FILE: str = "herbivore.weights.h5"
DEFAULT_CARNIVORE_WEIGHTS_FILE: str = "carnivore.weights.h5"
NUM_TRAINING_TICKS: int = 100000


logger = logging.getLogger(__name__)


def _create_agents(session_maker: sessionmaker, training: bool,
                   carnivore_weights: str, herbivore_weights: str) -> Dict[DietType, DQNAgent]:
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
        DietType.HERBIVORE: DQNAgent(herbivore_weights, state_size, training=training, verbose=not training),
        DietType.CARNIVORE: DQNAgent(carnivore_weights, state_size, training=training, verbose=not training),
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
    parser.add_argument("--carnivore-weights", type=str,
                        default=DEFAULT_CARNIVORE_WEIGHTS_FILE,
                        help="File path for carnivore model weights")
    parser.add_argument("--herbivore-weights", type=str,
                        default=DEFAULT_HERBIVORE_WEIGHTS_FILE,
                        help="File path for herbivore model weights")
    args = parser.parse_args()

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    session_maker = sessionmaker(bind=engine)

    if args.train:
        setup_logging(console_log_enabled=False, log_filename="")
    else:
        setup_logging(console_log_enabled=args.console_log,
                      log_filename=args.log_file)

    agents = _create_agents(session_maker,
                            args.train, args.carnivore_weights,
                            args.herbivore_weights)

    if args.train:
        print(f"  Running simulation for {NUM_TRAINING_TICKS} ticks... ")
    else:
        print(f"Starting simulation loop with a {args.tick_timer}s tick... ")
    print("  Ctrl+C to exit.")

    tick: int = 0
    try:
        while True:
            start_time = time.time()

            tick += 1
            if args.train and tick % 10 == 0:
                print(f"\n--- Tick {tick} ---")
                print(
                    f"Herbivore Epsilon: {agents[DietType.HERBIVORE].epsilon:.3f}")
                print(
                    f"Carnivore Epsilon: {agents[DietType.CARNIVORE].epsilon:.3f}")

            if tick % 1000 == 0:
                print(f"\n--- Saing weights at tick {tick} ---")
                agents[DietType.HERBIVORE].save()
                agents[DietType.CARNIVORE].save()

            if args.train and tick > NUM_TRAINING_TICKS:
                break

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
            agents[DietType.HERBIVORE].save(HERBIVORE_WEIGHTS_FILE)
            agents[DietType.CARNIVORE].save(CARNIVORE_WEIGHTS_FILE)


if __name__ == "__main__":
    main()
