import random
from web_server import create_app, db
from simulation.models import Critter, DietType

# --- Configuration ---
NUM_PROGENITORS = 5


def seed_population():
    """
    Creates the initial population for the world.
    - Creates two 'dummy' parents.
    - Creates a number of progenitors with random stats.
    """
    print("Seeding world population...")

    # 1. Create two 'dummy' critters to act as parents for the first generation.
    # We must commit them first to get their IDs.
    # A simple way to handle the non-nullable parent constraint is to have them be their own parent.
    adam = Critter(parent_one_id=1, parent_two_id=1)
    steve = Critter(parent_one_id=2, parent_two_id=2)

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
    for i in range(NUM_PROGENITORS):
        progenitor = Critter(
            parent_one_id=adam.id,
            parent_two_id=steve.id,
            diet=DietType.HERBIVORE if random.random() > 0.7 else DietType.CARNIVORE,
            # Assign random stats
            speed=random.uniform(3.0, 7.0),
            size=random.uniform(3.0, 7.0),
            # Place them randomly in the world near the origin
            x=random.randint(-50, 50),
            y=random.randint(-50, 50),
        )
        progenitors.append(progenitor)

    db.session.add_all(progenitors)

    # 3. Commit the entire transaction to the database.
    db.session.commit()
    print(f"Successfully created {len(progenitors)} progenitor critters.")


if __name__ == "__main__":
    # We need an application context to interact with the database.
    app = create_app()
    with app.app_context():
        # Clear existing critters to re-seed.
        db.session.query(Critter).delete()
        db.session.commit()
        seed_population()
