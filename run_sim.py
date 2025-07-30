import argparse
import logging
import time
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from simulation.engine import run_simulation_tick
from simulation.logger import setup_logging
from simulation.world import World


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
    Session = sessionmaker(bind=engine)

    setup_logging(console_log_enabled=args.console_log, log_filename=args.log_file)

    session = Session()
    world = World(seed=Config.WORLD_SEED, session=session)

    print(f"Starting simulation loop with a {args.tick_timer}s tick... ")
    print("  Ctrl+C to exit.")
    while True:
        try:
            run_simulation_tick(world, session)
            session.commit()
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            logging.error(traceback.format_exc())
            traceback.print_exc()
            session.rollback()
            raise
        finally:
            session.close()

        time.sleep(args.tick_timer)


if __name__ == "__main__":
    main()
