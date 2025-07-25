from web_server import db
import datetime
import enum


class CauseOfDeath(enum.Enum):
    STARVATION = "starvation"
    THIRST = "thirst"
    OLD_AGE = "old_age"
    PREDATION = "predation"
    EXHAUSTION = "exhaustion"


class Player(db.Model):
    __tablename__ = "player"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)

    critters = db.relationship("Critter", back_populates="owner", lazy="dynamic")
    dead_critters = db.relationship(
        "DeadCritter", back_populates="owner", lazy="dynamic"
    )

    def to_dict(self):
        return {"id": self.id, "username": self.username}

    def __repr__(self):
        return f"<Player {self.id} {self.username}"


class Critter(db.Model):
    __tablename__ = "critter"

    id = db.Column(db.Integer, primary_key=True)

    # Core stats
    health = db.Column(db.Float, default=100.0)
    energy = db.Column(db.Float, default=100.0)
    hunger = db.Column(db.Float, default=0.0)
    thirst = db.Column(db.Float, default=0.0)

    # Genetics
    age = db.Column(db.Integer, default=0)
    speed = db.Column(db.Float, default=5.0)
    size = db.Column(db.Float, default=5.0)

    # Position
    x = db.Column(db.Integer, default=0)
    y = db.Column(db.Integer, default=0)

    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=True)
    owner = db.relationship("Player", back_populates="critters")

    parent_one_id = db.Column(db.Integer, db.ForeignKey("critter.id"), nullable=False)
    parent_two_id = db.Column(db.Integer, db.ForeignKey("critter.id"), nullable=False)

    @property
    def children(self):
        return Critter.query.filter(
            (Critter.parent_one_id == self.id) | (Critter.parent_two_id == self.id)
        ).all()

    def to_dict(self):
        # TODO: add more
        return {
            "id": self.id,
            "age": self.age,
            "x": self.x,
            "y": self.y,
            "energy": self.energy,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "owner_id": self.player_id,
        }

    def __repr__(self):
        return f"<Critter {self.id}>"


class DeadCritter(db.Model):
    __tablename__ = "dead_critter"

    id = db.Column(db.Integer, primary_key=True)
    # Store original id
    original_critter_id = db.Column(db.Integer, index=True, unique=True)

    # stats snapshot
    age = db.Column(db.Integer, nullable=False)
    cause_of_death = db.Column(db.Enum(CauseOfDeath))

    # genes snapshot
    speed = db.Column(db.Float)
    size = db.Column(db.Float)

    # player owner
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=True)
    owner = db.relationship("Player", back_populates="dead_critters")

    time_of_death = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    children = db.relationship(
        "Critter", secondary="dead_critter_children_association", lazy="subquery"
    )

    def to_dict(self):
        # TODO: add more
        return {"id": self.id, "owner_id": self.player_id}

    def __repr__(self):
        return f"<DeadCritter {self.critter_id} {self.original_critter_id}>"


dead_critter_children_association = db.Table(
    "dead_critter_children_association",
    db.Column(
        "dead_critter_id",
        db.Integer,
        db.ForeignKey("dead_critter.id"),
        primary_key=True,
    ),
    db.Column(
        "child_critter_id", db.Integer, db.ForeignKey("critter.id"), primary_key=True
    ),
)


class TileState(db.Model):
    __tablename__ = "tile_state"

    x = db.Column(db.Integer, primary_key=True)
    y = db.Column(db.Integer, primary_key=True)

    food_available = db.Column(db.Float, nullable=False)
