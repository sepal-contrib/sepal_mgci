from component.message import cm

__all__ = ["MATRIX_NAMES", "TABLE_NAMES", "NO_VALUE", "SCHEMA"]

MATRIX_NAMES = ["from_code", "to_code"]
TABLE_NAMES = ["code", "desc", "color"]

# Set a value for missing reclassifications
NO_VALUE = 999

SCHEMA = {
    "id": [cm.rec.table.schema.id, "number"],
    "lc_class": [cm.rec.table.schema.code, "number"],
    "desc": [cm.rec.table.schema.description, "string"],
    "color": [cm.rec.table.schema.color, "hexa"],
}
