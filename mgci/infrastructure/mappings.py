"""Read and write mapping CSV content without touching workspace files."""

import csv
from io import StringIO

from mgci.domain.codes import normalize_mapping
from mgci.errors import LocalizedError


def parse_mapping(content, selected):
    reader = csv.DictReader(StringIO(content.decode('utf-8-sig'), newline=''), strict=True)
    fields = reader.fieldnames or []
    if not {'from_code', 'to_code'} <= set(fields) or len(fields) != len(set(fields)):
        raise LocalizedError('mapping_columns')
    loaded = dict(normalize_mapping((row['from_code'], row['to_code']) for row in reader))
    if not selected.evidence:
        raise LocalizedError('mapping_no_classes')
    # Target 0 leaves a class unassigned, rows for classes not
    # in the table are ignored, and classes not in the file keep their current target.
    missing = sorted(set(loaded.values()) - set(selected.targets) - {0})
    if missing:
        raise LocalizedError('mapping_unknown_targets', classes=','.join(map(str, missing)))
    current = dict(selected.mapping)
    return tuple((code, loaded.get(code, current.get(code, 0))) for code in selected.evidence.classes)


def mapping_csv(mapping):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(('from_code', 'to_code'))
    writer.writerows(mapping)
    return stream.getvalue().encode('utf-8')
