import json
from typing import Any, Dict
from simulation.action_type import ActionType
from sqlalchemy import orm
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
    IDLE = "idle"
    FLEEING = "fleeing"
    RESTING = "resting"
    SEEKING_FOOD = "seeking food"
    EATING = "eating"
    SEEKING_WATER = "seeking water"
    DRINKING = "drinking"
    SEEKING_MATE = "seeking mate"
    BREEDING = "breeding"


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
    age = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    speed = db.Column(db.Float, nullable=False, default=5.0, server_default="5.0")
    size = db.Column(db.Float, nullable=False, default=5.0, server_default="5.0")
    metabolism = db.Column(db.Float, nullable=False, default=1.0, server_default="1.0")
    lifespan = db.Column(
        db.Integer, nullable=False, default=2000, server_default="2000"
    )

    # Position
    x = db.Column(db.Integer, default=0)
    y = db.Column(db.Integer, default=0)

    # Velocity
    vx = db.Column(db.Float, default=0.0)
    vy = db.Column(db.Float, default=0.0)

    movement_progress = db.Column(
        db.Float, nullable=False, default=0.0, server_default="0.0"
    )

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

    last_action = db.Column(db.Enum(ActionType), nullable=True)

    @property
    def children(self):
        return Critter.query.filter(
            (Critter.parent_one_id == self.id) | (Critter.parent_two_id == self.id)
        ).all()

    @property
    def max_health(self) -> float:
        return self.size * HEALTH_PER_SIZE_POINT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "health" not in kwargs:
            self.health = self.size * HEALTH_PER_SIZE_POINT

        # A transient, in-memory flag to mark if a critter has died this tick.
        self.is_ghost: bool = False

    @orm.reconstructor
    def init_on_load(self):
        """
        Called by SQLAlchemy every time a Critter is loaded from the database.
        """
        # Initialize transient attributes.
        self.is_ghost = False

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, enum.Enum):
                data[column.name] = value.name if value else None
            else:
                data[column.name] = value
        return data

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
    herbivore_age_distribution = db.Column(db.Text)
    carnivore_age_distribution = db.Column(db.Text)
    herbivore_health_distribution = db.Column(db.Text)
    carnivore_health_distribution = db.Column(db.Text)
    herbivore_hunger_distribution = db.Column(db.Text)
    carnivore_hunger_distribution = db.Column(db.Text)
    herbivore_thirst_distribution = db.Column(db.Text)
    carnivore_thirst_distribution = db.Column(db.Text)
    herbivore_energy_distribution = db.Column(db.Text)
    carnivore_energy_distribution = db.Column(db.Text)

    goal_distribution = db.Column(db.Text)

    def to_dict(self):
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, str) and column.name.endswith("_distribution"):
                data[column.name] = json.loads(value) if value else {}
            elif isinstance(value, datetime):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        return data
