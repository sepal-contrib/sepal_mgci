"""Versioned background provenance and safe Earth Engine CSV ingestion."""

import ast
import csv
from dataclasses import asdict
from io import StringIO
import json
import re

from mgci.application.state import Request
from mgci.domain.configuration import Configuration, DatasetEvidence, ImageSelection, IndicatorConfig, ScalePolicy, TransitionTable, Workflow
from mgci.domain.provenance import scientific_identity
from mgci.errors import LocalizedError


def encode_request(request: Request) -> dict:
    return json.loads(json.dumps(asdict(request), allow_nan=False))


def decode_request(record: dict) -> Request:
    try:
        values = dict(record['configuration'])
        for key in ('a', 'b'):
            selected = dict(values[key])
            if selected['evidence']:
                evidence = dict(selected['evidence'])
                evidence['images'] = tuple(evidence['images'])
                evidence['classes'] = tuple(evidence['classes'])
                selected['evidence'] = DatasetEvidence(**evidence)
            selected['mapping'] = tuple(tuple(pair) for pair in selected['mapping'])
            selected['targets'] = tuple(selected['targets'])
            selected['labels'] = tuple(tuple(row) for row in selected.get('labels', ()))
            selected['images'] = tuple(ImageSelection(**image) for image in selected['images'])
            values[key] = IndicatorConfig(**selected)
        values['workflow'] = Workflow(values['workflow'])
        values['scale'] = ScalePolicy(**values['scale'])
        values['reporting_intervals'] = tuple(values['reporting_intervals'])
        if values['transition']:
            table = dict(values['transition'])
            table['rows'] = tuple(tuple(row) for row in table['rows'])
            values['transition'] = TransitionTable(**table)
        config = Configuration(**values)
        fields = {**record, 'configuration': config, 'slot': tuple(record['slot'])}
        request = Request(**fields)
        if request.slot[1] != 'statistics' or request.identity != scientific_identity(config, *request.slot[:2]):
            raise LocalizedError('task_provenance_mismatch')
        return request
    except (KeyError, TypeError, IndexError) as error:
        raise LocalizedError('task_provenance_invalid') from error


def parse_task_csv(content: bytes) -> dict:
    reader = csv.DictReader(StringIO(content.decode('utf-8-sig'), newline=''))
    results = {}
    for row in reader:
        key = row.get('process_id', '')
        if not re.fullmatch(r'\d+(?:_\d+_\d+)?', key) or key in results:
            raise LocalizedError('task_result_identifier')
        categories = ('sub_a',) if '_' not in key else (
            'baseline_degradation', 'final_degradation', 'baseline_transition', 'report_transition')
        parsed = {}
        for category in categories:
            text = row.get(category, '')
            # EE CSV uses {name=value}; JSON and Python literal maps also occur.
            text = re.sub(r'([A-Za-z_]\w*)\s*=', r'"\1":', text)
            try:
                value = ast.literal_eval(text)
            except (ValueError, SyntaxError) as error:
                raise LocalizedError('task_result_category', category=category) from error
            if not isinstance(value, list):
                raise LocalizedError('task_result_rows')
            parsed[category] = value
        results[key] = parsed
    if not results:
        raise LocalizedError('task_result_empty')
    return results


def validate_results(request, payload):
    from mgci.domain.reporting import reporting_breakpoints

    config = request.configuration
    images = getattr(config, request.slot[0]).images
    if request.slot[0] == 'a':
        expected = {str(image.year) for _, sources in reporting_breakpoints(images, config.reporting_intervals) for image in sources}
        categories = {'sub_a'}
    else:
        expected = {f'{images[0].year}_{images[1].year}_{image.year}' for image in images[2:]}
        categories = {'baseline_degradation', 'final_degradation', 'baseline_transition', 'report_transition'}
    if set(payload) != expected or any(set(value) != categories for value in payload.values()):
        raise LocalizedError('task_results_incomplete')
