# Critter World Simulation

This project is a persistent, procedurally generated world populated by evolving critters. It consists of two main components: a standalone simulation engine that runs continuously in the background, and a Flask web server that provides a real-time visualization of the world.

## Project Structure

```
creature_world/
├── simulation/         # Core simulation logic, AI, and models
├── web_server/         # Flask web application for visualization
├── tests/              # Unit tests for the simulation
├── run_sim.py          # Script to run the simulation loop
├── run_web.py          # Script to run the web server
├── seed_world.py       # Script to seed the initial population
├── migrate_db.sh       # Helper script for database migrations
├── requirements.txt    # Python requirements
└── config.py           # Configuration file
```

## Setup

1.  **Install Dependencies:** Ensure you have Python installed. It's recommended to use a virtual environment.
    ```bash
    # Create and activate a virtual environment
    python -m venv .venv
    source .venv/bin/activate

    # Install required packages
    pip install -r requirements.txt
    ```

2.  **Initialize the Database:** Before running for the first time, you need to create the database and apply all migrations.
    ```bash
    # Initialize the migration repository (only for the very first setup)
    export FLASK_APP=run_web.py
    export FLASK_DEBUG=1
    flask db init

    # Create the first migration and upgrade the database
    ./migrate_db.sh "Initial migration"
    ```

## How to Run

The simulation requires two separate processes to be running in two different terminals.

### 1. Seed the World (One-time setup)

Before starting the simulation for the first time, you must seed it with an initial population of critters.

To start a completely fresh simulation, use the `--clear-history` flag. This will wipe all existing critters, historical data, and statistics.

```bash
# Example: Create a new world with 100 progenitors, clearing all old data
python seed_world.py --num-progenitors 100 --clear-history
```

#### Options:

* `--num-progenitors` or `-n`: The number of initial critters to create (Default: 50).

* `--clear-history`: Wipes all simulation tables (`Critter`, `DeadCritter`, `SimulationStats`, `TileState`) before seeding.

### 2. Run the Simulation Engine
In your first terminal, start the continuous simulation loop. This process will run indefinitely, updating the world state.

```bash
# Run the simulation with a 2-second tick timer and console logging enabled
python run_sim.py --tick-timer 2.0 --console-log
```

or just use `run_sim.sh`.

#### Options:
* `-t`, `--tick-timer`: The time in seconds between sim ticks (Default: 5.0)
* `--console-log`: Enable logging to the console (logs will still go to the file).
* `--log-file`: The name of the file to save logs to (Default: `simulation.log`)

### 3. Run the Web Server
In a second terminal, start the Flask web server.  This provides the map and stats pages.

```bash
# Set the required environment variables
export FLASK_APP=run_web.py
export FLASK_DEBUG=1

# Run the server
flask run
```

or just use `run_web.sh`.

---

You can now access the visualizations in your browser:

Map View: http://127.0.0.1:5000/

Statistics Page: http://127.0.0.1:5000/stats