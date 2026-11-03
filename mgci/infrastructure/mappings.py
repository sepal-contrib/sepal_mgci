"""Read and write mapping CSV content without touching workspace files."""

import csv
from io import StringIO

from mgci.domain.codes import normalize_mapping


def parse_mapping(content, selected):
    reader = csv.DictReader(StringIO(content.decode('utf-8-sig'), newline=''), strict=True)
    fields = reader.fieldnames or []
    if not {'from_code', 'to_code'} <= set(fields) or len(fields) != len(set(fields)):
        raise ValueError('Mapping needs from_code and to_code columns')
    mapping = normalize_mapping((row['from_code'], row['to_code']) for row in reader)
    if not selected.evidence:
        raise ValueError('Get the source classes before loading a mapping')
    if set(dict(mapping)) != set(selected.evidence.classes):
        raise ValueError('Mapping must contain every source class exactly once')
    if not set(dict(mapping).values()) <= set(selected.targets):
        raise ValueError('Mapping contains unassigned or unknown target classes')
    return mapping


def mapping_csv(mapping):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(('from_code', 'to_code'))
    writer.writerows(mapping)
    return stream.getvalue().encode('utf-8')
