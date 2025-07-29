from simulation.behaviours.flocking import FlockingBehavior
from simulation.behaviours.wandering import WanderingBehavior
from simulation.models import DietType
from simulation.behaviours.water_seeking import WaterSeekingBehavior
from simulation.behaviours.mate_seeking import MateSeekingBehavior
from simulation.behaviours.grazing import GrazingBehavior
from simulation.behaviours.fleeing import FleeingBehavior
from simulation.behaviours.hunting import HuntingBehavior
from simulation.brain import CritterAI


def create_ai_for_critter(critter, world, all_critters):
    """
    Factory function that assembles the correct AI brain and modules
    based on the critter's diet.
    """
    shared_modules = {
        "water_seeking": WaterSeekingBehavior(),
        "mate_seeking": MateSeekingBehavior(),
    }

    if critter.diet == DietType.HERBIVORE:
        herbivore_modules = {
            "foraging": GrazingBehavior(),
            "fleeing": FleeingBehavior(),
            "moving": FlockingBehavior(),
        }
        modules = {**shared_modules, **herbivore_modules}

    elif critter.diet == DietType.CARNIVORE:
        carnivore_modules = {
            "foraging": HuntingBehavior(),
            "moving": WanderingBehavior(),
        }
        modules = {**shared_modules, **carnivore_modules}

    else:
        raise NotImplementedError(f"unknown diet {critter.diet}")

    return CritterAI(critter, world, all_critters, modules)
