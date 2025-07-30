from abc import ABC, abstractmethod
from typing import Any, Dict, List

from simulation.models import Critter
from simulation.world import World


class Behavior(ABC):
    """A common abstract base class for all AI behavior modules."""

    @abstractmethod
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Dict[str, Any]:
        pass
