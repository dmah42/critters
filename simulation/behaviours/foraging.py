from abc import abstractmethod
from typing import List, Optional

from simulation.behaviours.behavior import AIAction, Behavior
from simulation.models import Critter
from simulation.world import World


class ForagingBehavior(Behavior):
    """
    An abstract base class that defines the contract for all foraging
    behaviors (e.g., grazing, hunting).
    """

    @abstractmethod
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Optional[AIAction]:
        """
        Determines the foraging-related action for a critter.
        This method must be implemented by all subclasses.

        Args:
            critter: The critter making the decision.
            world: The world object, for checking terrain and food.
            all_critters: The list of all critters, for finding prey/mates.

        Returns:
            A complete action dictionary (e.g., EAT, ATTACK, SEEK_FOOD), or None.
        """
        pass
