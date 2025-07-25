from flask import request, jsonify, Blueprint, render_template
from simulation.models import Player, Critter, DeadCritter, TileState
from simulation.engine import World

from web_server import db
from flask import current_app as app


main = Blueprint("main", __name__)


CANVAS_SIZE = 600


@main.route("/")
def index():
    return render_template("index.html", canvas_size=CANVAS_SIZE)


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


@main.route("/api/world/view")
def get_world_view_data():
    """Returns tile data for a rectangular area."""
    center_x = request.args.get("x", default=0, type=int)
    center_y = request.args.get("y", default=0, type=int)
    width = request.args.get("w", default=50, type=int)
    height = request.args.get("h", default=50, type=int)

    # FIXME: this shouldn't be set here.
    world = World(seed=1)

    tile_data = []
    start_x = center_x - (width // 2)
    end_x = start_x + width
    start_y = center_y - (height // 2)
    end_y = start_y + height

    critters_in_view = Critter.query.filter(
        Critter.x.between(start_x, end_x - 1), Critter.y.between(start_y, end_y - 1)
    ).all()
    critter_data = [critter.to_dict() for critter in critters_in_view]

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

    return jsonify({"tiles": tile_data, "critters": critter_data})


if __name__ == "__main__":
    app.run(debug=True)
