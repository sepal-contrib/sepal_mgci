"""Read custom B labels and colours without modifying the source CSV."""

import csv
from io import StringIO
import re

from mgci.domain.codes import class_code
from mgci.errors import LocalizedError


def parse_classification(content):
    reader = csv.DictReader(StringIO(content.decode('utf-8-sig'), newline=''), strict=True)
    fields = reader.fieldnames or []
    if not {'lc_class', 'desc', 'color'} <= set(fields) or len(fields) != len(set(fields)):
        raise LocalizedError('classification_columns')
    labels = {}
    for row in reader:
        code = class_code(row['lc_class'])
        name, color = (row['desc'] or '').strip(), (row['color'] or '').strip()
        if code in labels or not 1 <= code <= 99 or not name or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise LocalizedError('classification_rows')
        labels[code] = (name, color)
    if not labels:
        raise LocalizedError('classification_empty')
    return tuple((code, *labels[code]) for code in sorted(labels))
