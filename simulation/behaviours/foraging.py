from abc import ABC, abstractmethod


class ForagingBehavior(ABC):
    """
    An abstract base class that defines the contract for all foraging
    behaviors (e.g., grazing, hunting).
    """

    @abstractmethod
    def get_action(self, critter, world, all_critters):
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
