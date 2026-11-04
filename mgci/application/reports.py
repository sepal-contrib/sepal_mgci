"""Explicit report revisions keep scientific artifacts and their metadata intact."""

from dataclasses import dataclass
from uuid import uuid4

from .state import Artifact


@dataclass(frozen=True)
class ReportRevision:
    report_id: str
    artifacts: tuple[Artifact, ...]
    aoi_name: str
    ref_area: str
    source: str
    aoi_label: str = ''
    session_id: int = 0
    sequence: int = 1

    @property
    def folder(self):
        return f'SDG1542_{self.aoi_label}'

    @property
    def filename(self):
        # Name: SDG1542_<AOI><session>[_sub_a|_sub_b].xlsx. Later exports in
        # the same session get a counter instead of overwriting earlier reports.
        keys = tuple(artifact.request.slot[0] for artifact in self.artifacts)
        which = '' if keys == ('a', 'b') else f'_sub_{keys[0]}'
        counter = '' if self.sequence == 1 else f'_{self.sequence}'
        return f'{self.folder}{self.session_id}{which}{counter}.xlsx'


def prepare_report(state, indicators, session_id=0, sequence=1) -> ReportRevision:
    selected = tuple(indicators)
    if not selected or len(set(selected)) != len(selected) or any(key not in ('a', 'b') for key in selected):
        raise ValueError('Select at least one indicator for the report')
    artifacts = []
    for key in selected:
        artifact = state.current(key, 'statistics')
        if artifact is None:
            raise ValueError(f'Calculate sub-indicator {key.upper()} before downloading its report')
        artifacts.append(state.export_artifact(artifact.request))
    config = state.configuration
    return ReportRevision(str(uuid4()), tuple(artifacts), config.aoi_name, config.ref_area, config.source,
                          config.aoi_label, session_id, sequence)
