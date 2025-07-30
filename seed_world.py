import argparse
import random
from config import Config
from simulation.engine import TerrainType
from simulation.world import World
from web_server import create_app, db
from simulation.models import Critter, DeadCritter, DietType, SimulationStats, TileState


def seed_population(seed, num_progenitors):
    """
    Creates the initial population for the world.
    - Creates two 'dummy' parents.
    - Creates a number of progenitors with random stats.
    """
    print(f"Seeding world with seed {seed} and {num_progenitors} progenitors")

    world = World(seed=seed, session=db.session)

    # 1. Create two 'dummy' critters to act as parents for the first generation.
    # We must commit them first to get their IDs.
    # A simple way to handle the non-nullable parent constraint is to have them be their own parent.
    adam = Critter(parent_one_id=1, parent_two_id=1, size=5.0)
    steve = Critter(parent_one_id=2, parent_two_id=2, size=5.0)

    # Add them to the session and flush to assign IDs without committing the full transaction.
    db.session.add(adam)
    db.session.add(steve)
    db.session.flush()

    # Now we can update them to reference their own IDs correctly.
    adam.parent_one_id = adam.id
    adam.parent_two_id = adam.id
    steve.parent_one_id = steve.id
    steve.parent_two_id = steve.id

    print(f"Created dummy parents with IDs: {adam.id} and {steve.id}")

    # Create the progenitor critters with random stats.
    progenitors = []
    for _ in range(num_progenitors):
        while True:
            rand_x = random.randint(-200, 200)
            rand_y = random.randint(-200, 200)

            tile = world.get_tile(rand_x, rand_y)

            if tile["terrain"] != TerrainType.WATER:
                break

        progenitor = Critter(
            parent_one_id=adam.id,
            parent_two_id=steve.id,
            diet=random.choice([DietType.HERBIVORE, DietType.CARNIVORE]),
            # Assign random stats
            speed=random.uniform(3.0, 7.0),
            size=random.uniform(3.0, 7.0),
            # Place them randomly in the world near the origin
            x=rand_x,
            y=rand_y,
        )
        progenitors.append(progenitor)

    db.session.add_all(progenitors)

    # 3. Commit the entire transaction to the database.
    db.session.commit()
    print(f"Successfully created {len(progenitors)} progenitor critters.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the critter world")
    parser.add_argument(
        "-n",
        "--num-progenitors",
        type=int,
        default=20,
        help="The number of initial progenitors to create",
    )
    parser.add_argument(
        "--clear-history",
        action="store_true",  # This makes it a boolean flag
        help="Clear all existing critters, dead critters, and statistics before seeding.",
    )
    args = parser.parse_args()

    # We need an application context to interact with the database.
    app = create_app()
    with app.app_context():
        if args.clear_history:
            # Clear existing critters to re-seed.
            db.session.query(Critter).delete()
            db.session.query(DeadCritter).delete()
            db.session.query(TileState).delete()
            db.session.query(SimulationStats).delete()
            db.session.commit()
            print("All data cleared")

        seed_population(seed=Config.WORLD_SEED, num_progenitors=args.num_progenitors)
