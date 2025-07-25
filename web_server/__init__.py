from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config


db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=Config):
    """App factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Import models from the simulation package HERE.
    # This makes them available to Flask-SQLAlchemy and Flask-Migrate.
    from simulation.models import Player, Critter, TileState, DeadCritter

    db.init_app(app)
    migrate.init_app(app, db)

    from web_server.routes import main as main_bp

    app.register_blueprint(main_bp)

    return app
