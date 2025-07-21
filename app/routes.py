from flask import request, jsonify, Blueprint
from app import create_app
from app.models import Player, Critter, DeadCritter
from app.simulation import World, TerrainType

from app import db
from flask import current_app as app


main = Blueprint("main", __name__)


@main.route("/")
def index():
    return "Welcome to Critter World"


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


@main.route("/world/view")
def world_view():
    """
    Generates a simple HTML page to visualize a slice of the world.
    Acceps query parameters: x, y, w, h.
    """
    center_x = request.args.get("x", default=0, type=int)
    center_y = request.args.get("y", default=0, type=int)
    width = request.args.get("w", default=50, type=int)
    height = request.args.get("h", default=50, type=int)

    # FIXME: this shouldn't be set here.
    world = World(seed=12345)

    color_map = {
        TerrainType.WATER: "#4287f5",
        TerrainType.GRASS: "#34a12d",
        TerrainType.DIRT: "#855a38",
        TerrainType.MOUNTAIN: "#999999",
    }

    html = [
        "<html><head><title>World View</title><style>",
        "table {border-collapse: collapse; font-family: monospace}",
        "td {width: 20px; height: 20px; text-align: center; color: white; font-size: 8px; font-weight: bold;}",
        "</style></head><body>",
    ]
    html.append("<table>")

    start_x = center_x - (width // 2)
    start_y = center_y - (width // 2)

    for y in range(height):
        html.append("<tr>")
        for x in range(width):
            tile = world.get_tile(start_x + x, start_y + y)
            terrain_type = tile["terrain"]
            color = color_map.get(terrain_type, "#ffffff")

            tooltip = f"Coord: ({tile['x']}, {tile['y']})\nTerrain: {terrain_type.name}\nFood: {tile['food_available']:.1f}"
            height_text = f"{tile['height']:.1f}"
            html.append(
                f'<td style="background-color: {color};" title="{tooltip}">{height_text}</td>'
            )
        html.append("</tr>")

    html.append("</table></body></html>")

    return "".join(html)


if __name__ == "__main__":
    app.run(debug=True)
