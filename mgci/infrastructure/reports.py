"""Generate existing workbook layouts entirely from captured artifacts."""

from collections.abc import Mapping
from dataclasses import replace
from types import SimpleNamespace

from mgci.application.state import Artifact
from mgci.domain.reporting import reporting_breakpoints


def plain_data(value):
    if isinstance(value, Mapping):
        return {key: plain_data(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [plain_data(item) for item in value]
    return value


class _WorkbookSink:
    def __init__(self):
        self.content = None

    def mkdir(self, path, parents=False):
        return path

    def write(self, path, content, overwrite=False):
        self.content = bytes(content)
        return path


def build_workbook(artifacts: tuple[Artifact, ...]) -> bytes:
    from component.scripts.scripts import export_reports

    if not artifacts or len({a.request.slot[0] for a in artifacts}) != len(artifacts):
        raise ValueError('Select one statistics artifact per indicator')
    if any(a.request.slot[1] != 'statistics' for a in artifacts):
        raise ValueError('Reports require statistics artifacts')
    config = artifacts[0].request.configuration
    shared = lambda c: (c.aoi_identity, c.aoi_graph, c.aoi_name, c.ref_area, c.source,
                        c.scale, c.rsa, c.dem, c.biobelt, c.units, c.algorithm_version)
    if any(shared(a.request.configuration) != shared(config) for a in artifacts):
        raise ValueError('Combined reports require compatible shared inputs and metadata')
    results = {}
    a_years, b_years = {}, {}
    transition = None
    for artifact in artifacts:
        captured = artifact.request.configuration
        indicator = artifact.request.slot[0]
        results.update(plain_data(artifact.payload))
        images = getattr(captured, indicator).images
        if indicator == 'a':
            a_years = {year: [{'asset': image.asset, 'year': image.year} for image in sources]
                       for year, sources in reporting_breakpoints(images, captured.reporting_intervals)}
        else:
            b_years = {'baseline': {'base': {'asset': images[0].asset, 'year': images[0].year},
                                   'report': {'asset': images[1].asset, 'year': images[1].year}}}
            b_years.update({index: {'asset': image.asset, 'year': image.year}
                            for index, image in enumerate(images[2:], start=2)})
            transition = captured.transition
    sink = _WorkbookSink()
    export_reports(results, a_years, b_years, config.aoi_name, config.ref_area,
                   config.source, transition, 'reports', artifacts[0].request.request_id,
                   which='both' if len(artifacts) == 2 else f'sub_{artifacts[0].request.slot[0]}',
                   sepal_client=SimpleNamespace(files=sink))
    if sink.content is None:
        raise ValueError('Report generation produced no workbook')
    return sink.content


def build_report_revision(revision) -> bytes:
    """Apply explicitly captured report metadata to copies, never to stored results."""
    artifacts = tuple(Artifact(replace(artifact.request, configuration=replace(
        artifact.request.configuration, aoi_name=revision.aoi_name,
        ref_area=revision.ref_area, source=revision.source)), artifact.payload)
        for artifact in revision.artifacts)
    return build_workbook(artifacts)


def build_historical_workbook(payload, model_state, transition=None):
    """Rebuild the workbook of a task record from an earlier version, without making it current."""
    from component.scripts.scripts import export_reports

    has_a = any('_' not in key for key in payload)
    has_b = any('_' in key for key in payload)
    if has_b and transition is None:
        raise ValueError('Select the original transition CSV to reconstruct this historical B report')
    sink = _WorkbookSink()
    export_reports(plain_data(payload),
                   {int(year): sources for year, sources in model_state['reporting_years_sub_a'].items()},
                   model_state['sub_b_year'], model_state['geo_area_name'], model_state['ref_area'],
                   model_state['source_detail'], transition, 'reports', model_state['session_id'],
                   which='both' if has_a and has_b else 'sub_a' if has_a else 'sub_b',
                   sepal_client=SimpleNamespace(files=sink))
    if sink.content is None:
        raise ValueError('Historical report generation produced no workbook')
    return sink.content
