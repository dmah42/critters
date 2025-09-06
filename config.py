import os

# Get the absolute path of this file
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Database URI. SQLite file.
    _SQLALCHEMY_DATABASE_URI_BASE = (
        "sqlite:///" + os.path.join(basedir, "app.db")
    )
    SQLALCHEMY_DATABASE_URI = _SQLALCHEMY_DATABASE_URI_BASE + "?mode=ro"
    SQLALCHEMY_SIM_DATABASE_URI = _SQLALCHEMY_DATABASE_URI_BASE

    # Disable change tracking.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WORLD_SEED = 42
