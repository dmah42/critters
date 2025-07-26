import argparse
import time
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from simulation.engine import World, run_simulation_tick


def main():
    parser = argparse.ArgumentParser(description="Run Critter World sim loop")
    parser.add_argument(
        "-t",
        "--tick-timer",
        type=float,
        default=10.0,
        help="The time in seconds between sim ticks",
    )
    args = parser.parse_args()

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)

    world = World(seed=1)

    print(f"Starting simulation loop with a {args.tick_timer}s tick... ")
    print("  Ctrl+C to exit.")
    while True:
        session = Session()
        try:
            run_simulation_tick(world, session)
            session.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()

        time.sleep(args.tick_timer)


if __name__ == "__main__":
    main()
