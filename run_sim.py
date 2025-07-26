import time
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from simulation.engine import World, run_simulation_tick


def main():
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)

    world = World(seed=1)

    print("Starting simulation loop... Press Ctrl+C to exit.")
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

        time.sleep(60)


if __name__ == "__main__":
    main()
