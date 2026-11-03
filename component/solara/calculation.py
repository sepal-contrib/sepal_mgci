"""Statistics action using the common request lifecycle."""

import solara

from .actions import RequestAction
from .messages import msg


@solara.component
def StatisticsAction(state, publish, indicator: str, run, prepare=None):
    RequestAction(state, publish, indicator, 'statistics', run, prepare=prepare,
                  label=msg('calculation.run', indicator=indicator.upper()))
