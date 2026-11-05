"""Read transition bytes without modifying the selected workspace file."""

import csv
from hashlib import sha256
from io import StringIO

from mgci.domain.codes import class_code
from mgci.domain.configuration import TransitionTable
from mgci.errors import LocalizedError


def parse_transition(content: bytes, source: str) -> TransitionTable:
    try:
        reader = csv.DictReader(StringIO(content.decode('utf-8-sig'), newline=''), strict=True)
        required = {'from_code', 'to_code', 'impact_code'}
        headers = reader.fieldnames or []
        if not required <= set(headers) or len(headers) != len(set(headers)):
            raise LocalizedError('transition_columns')
        rows = []
        pairs = set()
        for raw in reader:
            if None in raw:
                raise LocalizedError('transition_extra_fields')
            row = tuple(class_code(raw[column]) for column in ('from_code', 'to_code', 'impact_code'))
            if row[:2] in pairs or row[2] not in (1, 2, 3):
                raise LocalizedError('transition_rows')
            pairs.add(row[:2])
            rows.append(row)
        if not rows:
            raise LocalizedError('transition_empty')
    except (UnicodeError, csv.Error) as error:
        raise LocalizedError('transition_invalid') from error
    return TransitionTable(tuple(sorted(rows)), source, sha256(content).hexdigest(), True)


async def load_transition(filesystem, path: str) -> TransitionTable:
    if not path:
        raise LocalizedError('transition_required')
    content = await filesystem.read_bytes_async(path)
    return parse_transition(content, path)
