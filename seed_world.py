import argparse
import random
from typing import List
from config import Config
from simulation.engine import TerrainType, _log_event
from simulation.world import World
from web_server import create_app, db
from simulation.models import (
    Critter,
    DeadCritter,
    DietType,
    Event,
    SimulationStats,
    TileState,
)


def seed_population(
    seed: int,
    num_herbivores: int,
    num_carnivores: int,
    spawn_radius: int,
    num_packs: int,
    pack_radius: int,
):
    """
    Creates the initial population for the world using pack-based seeding for carnivores.
    """
    print(f"Seeding world population...")

    world = World(seed=seed, session=db.session)

    # 1. Create two 'dummy' critters to act as parents for the first generation.
    # We must commit them first to get their IDs.
    # A simple way to handle the non-nullable parent constraint is to have them be their own parent.
    adam = Critter(parent_one_id=1, parent_two_id=1, size=5.0)
    steve = Critter(parent_one_id=2, parent_two_id=2, size=5.0)

    # Add them to the session and flush to assign IDs without committing the full transaction.
    db.session.add_all([adam, steve])
    db.session.flush()
    # Delete them from the session.  They never really existed...
    db.session.delete(adam)
    db.session.delete(steve)

    # Now we can update them to reference their own IDs correctly.
    adam.parent_one_id = adam.id
    adam.parent_two_id = adam.id
    steve.parent_one_id = steve.id
    steve.parent_two_id = steve.id

    print(f"Created dummy parents with IDs: {adam.id} and {steve.id}")

    # TODO: check for existing critter at each new position

    # Seed herbivores (scattered)
    herbivores: List[Critter] = []
    for _ in range(num_herbivores):
        while True:
            rand_x = random.randint(-spawn_radius, spawn_radius)
            rand_y = random.randint(-spawn_radius, spawn_radius)

            # Don't spawn in water.
            if world.get_tile(rand_x, rand_y).terrain != TerrainType.WATER:
                herbivores.append(
                    Critter(
                        parent_one_id=adam.id,
                        parent_two_id=steve.id,
                        diet=DietType.HERBIVORE,
                        # Assign random genetics
                        speed=random.uniform(3.0, 7.0),
                        size=random.uniform(3.0, 7.0),
                        metabolism=random.uniform(0.8, 1.2),
                        lifespan=random.randint(1800, 2200),
                        commitment=random.uniform(1.5, 2.5),
                        perception=random.uniform(4.0, 6.0),
                        # Place them randomly in the world near the origin
                        x=rand_x,
                        y=rand_y,
                    )
                )
                break
    db.session.add_all(herbivores)
    print(f"Created {len(herbivores)} herbivores")

    # Create pack centres for carnivores
    pack_centers = []
    for _ in range(num_packs):
        while True:
            rand_x = random.randint(-spawn_radius, spawn_radius)
            rand_y = random.randint(-spawn_radius, spawn_radius)
            if world.get_tile(rand_x, rand_y).terrain != TerrainType.WATER:
                pack_centers.append((rand_x, rand_y))
                break
    print(f"Created {len(pack_centers)} carnivore pack centres")

    # Seed carnivores in packs
    carnivores: List[Critter] = []
    for _ in range(num_carnivores):
        center_x, center_y = random.choice(pack_centers)
        while True:
            rand_x = random.randint(center_x - pack_radius, center_x + pack_radius)
            rand_y = random.randint(center_y - pack_radius, center_y + pack_radius)
            if world.get_tile(rand_x, rand_y).terrain != TerrainType.WATER:
                carnivores.append(
                    Critter(
                        parent_one_id=adam.id,
                        parent_two_id=steve.id,
                        diet=DietType.CARNIVORE,
                        # Assign random genetics
                        speed=random.uniform(3.0, 7.0),
                        size=random.uniform(3.0, 7.0),
                        metabolism=random.uniform(0.8, 1.2),
                        lifespan=random.randint(1800, 2200),
                        commitment=random.uniform(1.5, 2.5),
                        perception=random.uniform(8.0, 15.0),
                        # Place them randomly in the world near the origin
                        x=rand_x,
                        y=rand_y,
                    )
                )
                break
    db.session.add_all(carnivores)
    print(f"Created {len(carnivores)} carnivores")

    # Assign IDs to everyone.
    db.session.flush()

    all_progenitors = herbivores + carnivores
    for critter in all_progenitors:
        _log_event(
            session=db.session,
            critter_id=critter.id,
            tick=0,
            event=Event.BIRTH,
            description=f"Created as a progenitor of the world",
        )

    # 3. Commit the entire transaction to the database.
    db.session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the critter world")
    parser.add_argument(
        "-nh",
        "--num-herbivores",
        type=int,
        default=150,
        help="The number of initial herbivores to create",
    )
    parser.add_argument(
        "-nc",
        "--num-carnivores",
        type=int,
        default=50,
        help="The number of initial carnivores to create",
    )
    parser.add_argument(
        "-s",
        "--spawn-radius",
        type=int,
        default=200,
        help="The overall radius in which to spawn critters",
    )
    parser.add_argument(
        "-p",
        "--num-packs",
        type=int,
        default=4,
        help="Number of carnivore packs to spawn.",
    )
    parser.add_argument(
        "-r",
        "--pack-radius",
        type=int,
        default=15,
        help="Radius in which to spawn carnivores in a pack.",
    )
    parser.add_argument(
        "-w",
        "--wipe-history",
        action="store_true",  # This makes it a boolean flag
        help="Clear all existing critters, dead critters, and statistics before seeding.",
    )
    args = parser.parse_args()

    # We need an application context to interact with the database.
    app = create_app()
    with app.app_context():
        if args.wipe_history:
            # Clear existing critters to re-seed.
            db.session.query(Critter).delete()
            db.session.query(DeadCritter).delete()
            db.session.query(TileState).delete()
            db.session.query(SimulationStats).delete()
            db.session.commit()
            print("All data cleared")

        seed_population(
            seed=Config.WORLD_SEED,
            num_herbivores=args.num_herbivores,
            num_carnivores=args.num_carnivores,
            spawn_radius=args.spawn_radius,
            num_packs=args.num_packs,
            pack_radius=args.pack_radius,
        )
        db.session.commit()
        print("Seeding complete")
