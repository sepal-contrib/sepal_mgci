"""Derive chart tables from captured statistics, sharing the report parser."""

from mgci.domain.reporting import reporting_breakpoints
from .reports import plain_data


def chart_choices(artifact):
    images = getattr(artifact.request.configuration, artifact.request.slot[0]).images
    if artifact.request.slot[0] == 'a':
        return tuple((str(year), str(year)) for year, _ in reporting_breakpoints(images, artifact.request.configuration.reporting_intervals))
    return (('baseline', f'{images[0].year} → {images[1].year}'), *(
        (image.asset, f'{images[1].year} → {image.year}') for image in images[2:]))


def chart_frame(artifact, selection):
    from component.scripts.scripts import parse_to_year_a, parse_result

    if selection not in dict(chart_choices(artifact)):
        raise ValueError('Select a reporting period from the captured result')
    config = artifact.request.configuration
    payload = plain_data(artifact.payload)
    if artifact.request.slot[0] == 'a':
        years = {year: [{'asset': image.asset, 'year': image.year} for image in sources]
                 for year, sources in reporting_breakpoints(config.a.images, config.reporting_intervals)}
        return parse_to_year_a(payload, years, int(selection))
    images = config.b.images
    report = images[2] if selection == 'baseline' else next(image for image in images[2:] if image.asset == selection)
    key = f'{images[0].year}_{images[1].year}_{report.year}'
    category = 'baseline_transition' if selection == 'baseline' else 'report_transition'
    return parse_result({category: payload[key][category]}, single=False)
