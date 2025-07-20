from app import db


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)

    critters = db.relationship("Critter", back_populates="owner", lazy=True)

    def __repr__(self):
        return f"<Player {self.id} {self.username}"


class Critter(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)

    # Core stats
    health = db.Column(db.Float, default=100.0)
    energy = db.Column(db.Float, default=100.0)

    # Genetics
    speed = db.Column(db.Float, default=5.0)
    size = db.Column(db.Float, default=5.0)

    # Position
    x = db.Column(db.Integer, default=0)
    y = db.Column(db.Integer, default=0)

    owner = db.relationship("Player", back_populates="critters")

    def __repr__(self):
        return f"<Critter {self.id}>"
