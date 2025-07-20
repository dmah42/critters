from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from models import Player, Critter


@app.route("/")
def index():
    return "Welcome to Critters"


@app.route("/api/critter", methods=["POST"])
def create_critter():
    """
    Creates a critter. Expects a JSON body with a username.
    """
    data = request.get_json()
    if not data or "username" not in data:
        return jsonify({"error": "Missing username in request"}), 400

    username = data["username"]

    player = Player.query.filter_by(username=username).first()
    if not player:
        # If the player doesn't exist, create a new one
        # TODO: rethink this
        player = Player(username=username)
        db.session.add(player)

    new_critter = Critter(owner=player)
    db.session.add(new_critter)

    db.session.commit()

    response = {
        "message": "Critter created successfully",
        "critter_id": new_critter.id,
        "owner_id": player.id,
    }
    return jsonify(response), 201


if __name__ == "__main__":
    app.run(debug=True)
