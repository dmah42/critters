from simulation.action_type import ActionType
from simulation.behaviours.moving import MovingBehavior
from simulation.behaviours.wandering import WanderingBehavior
from simulation.models import DietType

FLOCKING_RADIUS = 8
SEPARATION_DISTANCE = 1.5  # How close is "too close"
SEPARATION_WEIGHT = 1.4  # How strongly to avoid neighbors
ALIGNMENT_WEIGHT = 1.1  # How strongly to match heading
COHESION_WEIGHT = 1.2  # How strongly to move to the center


class FlockingBehavior(MovingBehavior):
    def get_action(self, critter, world, all_critters):
        """
        Calculates a movement vector based on the Boids algorithm
        Returns a WANDER action with a specific direction, or None.
        """
        flockmates = [
            other
            for other in all_critters
            if other.id != critter.id
            and other.diet == DietType.HERBIVORE
            and abs(other.x - critter.x) <= FLOCKING_RADIUS
            and abs(other.y - critter.y) <= FLOCKING_RADIUS
        ]

        if not flockmates:
            # No mates nearby, use the standard wandering behaviour.
            return WanderingBehavior().get_action(critter, world, all_critters)

        num_flockmates = len(flockmates)

        # --- Rule 1: Cohesion ---
        center_x, center_y = 0, 0
        for mate in flockmates:
            center_x += mate.x
            center_y += mate.y

        center_x /= num_flockmates
        center_y /= num_flockmates
        cohesion_dx, cohesion_dy = center_x - critter.x, center_y - critter.y

        # --- Rule 2: Separation ---
        separation_dx, separation_dy = 0, 0

        for mate in flockmates:
            distance_sq = (mate.x - critter.x) ** 2 + (mate.y - critter.y) ** 2
            if distance_sq > 0 and distance_sq < SEPARATION_DISTANCE**2:
                separation_dx += (critter.x - mate.x) / distance_sq
                separation_dy += (critter.y - mate.y) / distance_sq

        # --- Rule 3: Alignment ---
        alignment_dx, alignment_dy = 0, 0
        for mate in flockmates:
            alignment_dx += mate.vx
            alignment_dy += mate.vy
        alignment_dx /= num_flockmates
        alignment_dy /= num_flockmates

        # Combine them
        final_dx = (
            (separation_dx * SEPARATION_WEIGHT)
            + (alignment_dx * ALIGNMENT_WEIGHT)
            + (cohesion_dx * COHESION_WEIGHT)
        )
        final_dy = (
            (separation_dy * SEPARATION_WEIGHT)
            + (alignment_dy * ALIGNMENT_WEIGHT)
            + (cohesion_dy * COHESION_WEIGHT)
        )

        return {"type": ActionType.MOVE, "dx": final_dx, "dy": final_dy}
