import enum
import logging

from simulation.models import WorldState
from sqlalchemy.orm import Session

_SEASON_DURATION: int = 250

logger = logging.getLogger(__name__)


class Season(enum.Enum):
    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3
    _NUM_SEASONS = 4


class SeasonManager:
    """
    Manages the seasonal cycle of the simulation.
    """

    def __init__(self):
        self._season = Season.SPRING

    def update(self, session: Session, tick: int):
        """Updates season based on tick"""
        prev_season = self._season
        season_index = int(tick / _SEASON_DURATION) % Season._NUM_SEASONS.value
        self._season = Season(season_index)
        if self._season != prev_season:
            logger.info(f"\n*** {self._season.name.title()} has arrived. ***")
            season_state = session.query(WorldState).filter_by(
                key='season').first()
            if not season_state:
                season_state = WorldState(key='season')
                session.add(season_state)
            season_state.value = self._season.name
            session.commit()

    @property
    def season(self) -> Season:
        return self._season


# Create a singleton instance
season_manager = SeasonManager()
