from flask import request, jsonify, Blueprint, render_template
from sqlalchemy import func
from config import Config
from simulation.brain import (
    ENERGY_TO_START_RESTING,
    ENERGY_TO_STOP_RESTING,
    HUNGER_TO_START_FORAGING,
    HUNGER_TO_STOP_FORAGING,
    THIRST_TO_START_DRINKING,
    THIRST_TO_STOP_DRINKING,
)
from simulation.models import Player, Critter, DeadCritter, SimulationStats, TileState
from simulation.engine import DEFAULT_GRASS_FOOD, World

from web_server import db
from flask import current_app as app


main = Blueprint("main", __name__)


CANVAS_SIZE = 600


@main.route("/")
def index():
    return render_template(
        "index.html", canvas_size=CANVAS_SIZE, default_grass_food=DEFAULT_GRASS_FOOD
    )


@main.route("/stats")
def stats():
    return render_template(
        "stats.html",
        energy_to_start_resting=ENERGY_TO_START_RESTING,
        energy_to_stop_resting=ENERGY_TO_STOP_RESTING,
        hunger_to_start_foraging=HUNGER_TO_START_FORAGING,
        hunger_to_stop_foraging=HUNGER_TO_STOP_FORAGING,
        thirst_to_start_drinking=THIRST_TO_START_DRINKING,
        thirst_to_stop_drinking=THIRST_TO_STOP_DRINKING,
    )


@main.route("/api/player", methods=["POST"])
def create_player():
    """
    Creates a new player.
    Expects a JSON body with a unique 'username'.
    """
    data = request.get_json()
    if not data or "username" not in data:
        return jsonify({"error": "Missing username in request body"}), 400

    username = data["username"]

    # Check if it exists.
    if Player.query.filter_by(username=username).first():
        return (
            jsonify({"error": f"Player with username {username} already exists"}),
            409,
        )

    new_player = Player(username=username)
    db.session.add(new_player)
    db.session.commit()

    response = {
        "message": "Player created successfully",
        "player_id": new_player.id,
        "username": new_player.username,
    }
    return jsonify(response), 201


@main.route("/api/player/<int:player_id>", methods=["GET"])
def get_player(player_id):
    """Get's a player's data by their ID"""
    player = Player.query.get_or_404(player_id)
    return jsonify(player.to_dict())


@main.route("/api/critter/<int:critter_id>", methods=["GET"])
def get_critter(critter_id):
    """Get's a critter's data by its ID"""
    critter = Critter.query.get_or_404(critter_id)
    return jsonify(critter.to_dict())


@main.route("/api/critter/<int:critter_id>/adopt", methods=["POST"])
def adopt_critter(critter_id):
    """
    Assigns an existing unowned critter to a player.
    Excepts a JSON body with a 'player_id'.
    """
    critter = Critter.query.get(critter_id)
    if not critter:
        return jsonify({"error": "Critter not found"}), 404

    # Check if it's adopted already.
    if critter.owner:
        return (
            jsonify(
                {
                    "error": f"Critter {critter_id} is already owned by {critter.owner.username}"
                }
            ),
            409,
        )

    data = request.get_json()
    if not data or "player_id" not in data:
        return jsonify({"error": "Missing player id in request"}), 400

    player_id = data["player_id"]

    player = Player.query.filter_by(id=player_id).first()
    if not player:
        return jsonify({"error": f"Player {player_id} does not exist"}), 404

    critter.owner = player

    db.session.commit()

    response = {
        "message": "Adoption successful",
        "critter_id": critter.id,
        "player_id": player.id,
    }
    return jsonify(response), 200


@main.route("/api/dead-critter", methods=["GET"])
def get_dead_critter():
    """
    Get's a single dead critter's data by one of its IDs.
    Use query parameters: ?id= or ?original_id=
    """
    dead_critter_id = request.args.get("id", type=int)
    original_critter_id = request.args.get("original_id", type=int)

    dead_critter = None

    if dead_critter_id:
        dead_critter = DeadCritter.query.get_or_404(dead_critter_id)
    elif original_critter_id:
        dead_critter = DeadCritter.query.filter_by(
            original_critter_id=original_critter_id
        ).first_or_404()
    else:
        return jsonify({"error": "An id or original_id parameter is required."}), 400

    return jsonify(dead_critter.to_dict())


@main.route("/api/world/terrain", methods=["GET"])
def get_world_terrain_data():
    """Returns tile data for a given rectangular viewing area."""
    center_x = request.args.get("x", default=0, type=int)
    center_y = request.args.get("y", default=0, type=int)
    width = request.args.get("w", default=50, type=int)
    height = request.args.get("h", default=50, type=int)

    world = World(seed=Config.WORLD_SEED)

    tile_data = []
    start_x = center_x - (width // 2)
    end_x = start_x + width
    start_y = center_y - (height // 2)
    end_y = start_y + height

    overrides_list = TileState.query.filter(
        TileState.x.between(start_x, end_x), TileState.y.between(start_y, end_y)
    ).all()

    overrides_map = {(tile.x, tile.y): tile for tile in overrides_list}

    step = 1
    if width > CANVAS_SIZE:
        step = width // CANVAS_SIZE

    for y_offset in range(0, height, step):
        for x_offset in range(0, width, step):
            current_x = start_x + x_offset
            current_y = start_y + y_offset

            tile = world.generate_tile(current_x, current_y)

            if (current_x, current_y) in overrides_map:
                tile["food_available"] = overrides_map[
                    (current_x, current_y)
                ].food_available

            tile["terrain"] = tile["terrain"].name
            tile_data.append(tile)

    return jsonify({"tiles": tile_data})


@main.route("/api/world/critters", methods=["GET"])
def get_world_critters_data():
    """Returns the critter data for a given rectangular view."""
    center_x = request.args.get("x", default=0, type=int)
    center_y = request.args.get("y", default=0, type=int)
    width = request.args.get("w", default=50, type=int)
    height = request.args.get("h", default=50, type=int)

    start_x = center_x - (width // 2)
    end_x = start_x + width
    start_y = center_y - (height // 2)
    end_y = start_y + height

    critters_in_view = Critter.query.filter(
        Critter.x.between(start_x, end_x - 1), Critter.y.between(start_y, end_y - 1)
    ).all()
    critter_data = [critter.to_dict() for critter in critters_in_view]

    return jsonify({"critters": critter_data})


@main.route("/api/stats/history", methods=["GET"])
def get_stats_histor():
    """Returns a history of simulation stats"""
    limit = request.args.get("limit", 100, type=int)

    stats_history = (
        SimulationStats.query.order_by(SimulationStats.tick.desc()).limit(limit).all()
    )

    stats_history.reverse()

    return jsonify([s.to_dict() for s in stats_history])


@main.route("/api/stats/deaths", methods=["GET"])
def get_death_stats():
    """
    Returns the aggregate count for each cause of death
    """
    death_counts = (
        db.session.query(DeadCritter.cause, func.count(DeadCritter.cause))
        .group_by(DeadCritter.cause)
        .all()
    )

    # Convert the list of tuples into a dict for the frontend.
    return jsonify(
        {cause.name: count for cause, count in death_counts if cause is not None}
    )


if __name__ == "__main__":
    app.run(debug=True)
