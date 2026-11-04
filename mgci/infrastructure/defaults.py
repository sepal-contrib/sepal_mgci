"""Read-only packaged defaults. No user workspace or session access."""

import csv
from dataclasses import replace
from datetime import date
from pathlib import Path

from mgci.domain.codes import normalize_mapping
from mgci.domain.configuration import Configuration, ImageSelection, IndicatorConfig, Workflow
from .transitions import parse_transition

PARAMETERS = Path(__file__).resolve().parents[2] / 'component' / 'parameter'


def initial_configuration(year: int | None = None) -> Configuration:
    year = date.today().year if year is None else year
    with (PARAMETERS / 'lc_map_matrix.csv').open(newline='') as stream:
        mapping = normalize_mapping((row['from_code'], row['to_code']) for row in csv.DictReader(stream))
    asset = 'users/amitghosh/sdg_module/esa/cci_landcover'
    # Default years: A starts with 2000 only,
    # B with the 2000-2015 baseline and a 2018 report.
    def images(years):
        return tuple(ImageSelection(f'{asset}/{year}', year) for year in years)
    a = IndicatorConfig(asset, mapping=mapping, images=images((2000,)))
    b = IndicatorConfig(asset, mapping=mapping, images=images((2000, 2015, 2018)))
    transition = parse_transition((PARAMETERS / 'transition_matrix.csv').read_bytes(), 'packaged:transition_matrix')
    return Configuration('', Workflow.DEFAULT, a, b,
                         transition=replace(transition, explicitly_selected=False), rsa=False,
                         reporting_intervals=(2000, 2005, 2010, 2015, *range(2018, year + 1, 3)))


def classification_labels(selected=None) -> tuple[tuple[int, str, str], ...]:
    if selected is not None and selected.labels:
        return selected.labels
    with (PARAMETERS / 'lc_classification.csv').open(newline='') as stream:
        return tuple((int(row['lc_class']), row['desc'], row['color']) for row in csv.DictReader(stream))
