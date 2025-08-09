from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

from simulation.action_type import ActionType
from simulation.models import Critter
from simulation.world import World


@dataclass
class AIAction:
    type: ActionType.MOVE
    dx: Optional[float] = None
    dy: Optional[float] = None
    target: Optional[Tuple[int, int]] = None
    target_critter: Optional[Critter] = None


class Behavior(ABC):
    """A common abstract base class for all AI behavior modules."""

    @abstractmethod
    def get_action(
        self, critter: Critter, world: World, all_critters: List[Critter]
    ) -> Optional[AIAction]:
        pass
