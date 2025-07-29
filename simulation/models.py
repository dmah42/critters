import json
from web_server import db
from datetime import datetime, timezone
import enum

HEALTH_PER_SIZE_POINT = 20.0


class CauseOfDeath(enum.Enum):
    STARVATION = "starvation"
    THIRST = "thirst"
    OLD_AGE = "old_age"
    PREDATION = "predation"
    EXHAUSTION = "exhaustion"


class DietType(enum.Enum):
    HERBIVORE = "herbivore"
    CARNIVORE = "carnivore"


class AIState(enum.Enum):
    IDLE = "idle"  # Default state, making decisions
    RESTING = "resting"  # Committed to resting
    THIRSTY = "thirsty"  # Committed to finding and drinking water
    HUNGRY = "hungry"  # Committed to finding and eating food


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
    diet = db.Column(
        db.Enum(DietType),
        nullable=False,
        default=DietType.HERBIVORE,
        server_default=DietType.HERBIVORE.value,
    )
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

    # Avoid breeding too often
    breeding_cooldown = db.Column(db.Integer, default=0)

    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=True)
    owner = db.relationship("Player", back_populates="critters")

    parent_one_id = db.Column(db.Integer, db.ForeignKey("critter.id"), nullable=False)
    parent_two_id = db.Column(db.Integer, db.ForeignKey("critter.id"), nullable=False)

    ai_state = db.Column(
        db.Enum(AIState),
        nullable=False,
        default=AIState.IDLE,
        server_default=AIState.IDLE.value,
    )

    @property
    def children(self):
        return Critter.query.filter(
            (Critter.parent_one_id == self.id) | (Critter.parent_two_id == self.id)
        ).all()

    @property
    def max_health(self):
        return self.size * HEALTH_PER_SIZE_POINT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "health" not in kwargs:
            self.health = self.size * HEALTH_PER_SIZE_POINT

    def to_dict(self):
        # TODO: add more
        return {
            "id": self.id,
            "age": self.age,
            "diet": self.diet.name,
            "speed": self.speed,
            "size": self.size,
            "x": self.x,
            "y": self.y,
            "health": self.health,
            "max_health": self.max_health,
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
    original_id = db.Column(db.Integer, index=True, unique=True)

    # stats snapshot
    age = db.Column(db.Integer, nullable=False)
    cause = db.Column(db.Enum(CauseOfDeath))

    # genes snapshot
    speed = db.Column(db.Float)
    size = db.Column(db.Float)

    # player owner
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=True)
    owner = db.relationship("Player", back_populates="dead_critters")

    parent_one_id = db.Column(db.Integer)
    parent_two_id = db.Column(db.Integer)

    time_of_death = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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


class SimulationStats(db.Model):
    __tablename__ = "simulation_stats"
    tick = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    population = db.Column(db.Integer)
    herbivore_population = db.Column(db.Integer)
    carnivore_population = db.Column(db.Integer)

    # Store the age distribution as a JSON string
    age_distribution = db.Column(db.Text)
    health_distribution = db.Column(db.Text)
    hunger_distribution = db.Column(db.Text)
    thirst_distribution = db.Column(db.Text)
    energy_distribution = db.Column(db.Text)

    def to_dict(self):
        return {
            "tick": self.tick,
            "population": self.population,
            "herbivore_population": self.herbivore_population,
            "carnivore_population": self.carnivore_population,
            "age_distribution": (
                json.loads(self.age_distribution) if self.age_distribution else {}
            ),
            "health_distribution": (
                json.loads(self.health_distribution) if self.health_distribution else {}
            ),
            "hunger_distribution": (
                json.loads(self.hunger_distribution) if self.hunger_distribution else {}
            ),
            "thirst_distribution": (
                json.loads(self.thirst_distribution) if self.thirst_distribution else {}
            ),
            "energy_distribution": (
                json.loads(self.energy_distribution) if self.energy_distribution else {}
            ),
        }
