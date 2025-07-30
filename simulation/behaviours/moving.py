from abc import ABC, abstractmethod
from typing import Any, Dict, List

from simulation.models import Critter
from simulation.world import World


class MovingBehavior(ABC):
    """
    An abstract base class that defines the contract for all moving
    behaviors (e.g., flocking, wandering).
    """

    @abstractmethod
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Dict[str, Any]:
        """
        Determines the movement-related action for a critter.
        This method must be implemented by all subclasses.

        Args:
            critter: The critter making the decision.
            world: The world object, for checking terrain and food.
            all_critters: The list of all critters, for finding prey/mates.

        Returns:
            A complete action dictionary (e.g., EAT, ATTACK, SEEK_FOOD), or None.
        """
        pass
