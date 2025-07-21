from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from models import Player, Critter, DeadCritter


@app.route("/")
def index():
    return "Welcome to Critters"


@app.route("/api/player", methods=["POST"])
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


@app.route("/api/player/<int:player_id>", methods=["GET"])
def get_player(player_id):
    """Get's a player's data by their ID"""
    player = Player.query.get_or_404(player_id)
    return jsonify(player.to_dict())


@app.route("/api/critter/<int:critter_id>", methods=["GET"])
def get_critter(critter_id):
    """Get's a critter's data by its ID"""
    critter = Critter.query.get_or_404(critter_id)
    return jsonify(critter.to_dict())


@app.route("/api/critter/<int:critter_id>/adopt", methods=["POST"])
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


@app.route("/api/dead-critter", methods=["GET"])
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


if __name__ == "__main__":
    app.run(debug=True)
