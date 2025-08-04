import os

# Get the absolute path of this file
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Database URI. SQLite file.
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.db")

    # Disable change tracking.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WORLD_SEED = 42
