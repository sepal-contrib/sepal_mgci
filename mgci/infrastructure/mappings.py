"""Read and write mapping CSV content without touching workspace files."""

import csv
from io import StringIO

from mgci.domain.codes import normalize_mapping


def parse_mapping(content, selected):
    reader = csv.DictReader(StringIO(content.decode('utf-8-sig'), newline=''), strict=True)
    fields = reader.fieldnames or []
    if not {'from_code', 'to_code'} <= set(fields) or len(fields) != len(set(fields)):
        raise ValueError('Mapping needs from_code and to_code columns')
    loaded = dict(normalize_mapping((row['from_code'], row['to_code']) for row in reader))
    if not selected.evidence:
        raise ValueError('Get the source classes before loading a mapping')
    # Target 0 leaves a class unassigned, rows for classes not
    # in the table are ignored, and classes not in the file keep their current target.
    missing = sorted(set(loaded.values()) - set(selected.targets) - {0})
    if missing:
        raise ValueError(f"Some of the target land cover classes ({','.join(map(str, missing))}) "
                         'are not present in the destination land cover classes.')
    current = dict(selected.mapping)
    return tuple((code, loaded.get(code, current.get(code, 0))) for code in selected.evidence.classes)


def mapping_csv(mapping):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(('from_code', 'to_code'))
    writer.writerows(mapping)
    return stream.getvalue().encode('utf-8')
