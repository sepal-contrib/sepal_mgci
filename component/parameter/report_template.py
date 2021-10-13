# Stablish the template structure for the output tables.


# Define PIVOT variables to avoid breaks if someone wants to change a column
# report name.

MOUNTAINCLASS = "MountainClass"
LULCCLASS = "LULC_Class"
VALUE = "Value"
SERIESDESC = "SeriesDescription"
SERIESCOD = "SeriesCode"
UNITSNAME = "Units"
INDICATOR = "Indicator"
GEOAREANAM = "GeoAreaName"
TIMEPERIOD = "TimePeriod"
GEOAREACODE = "GeoAreaCode"

# ER_MTN_GRNCOV_276, ER_MTN_GRNCVI_276
# * The order will be used to display the report
BASE_COLS = [
    INDICATOR,
    "SeriesID",
    SERIESDESC,
    GEOAREACODE,
    GEOAREANAM,
    TIMEPERIOD,
    VALUE,
    "Time_Detail",
    "Source",
    "Footnote",
    "Nature",
    UNITSNAME,
    "Reporting",
    SERIESCOD,
    MOUNTAINCLASS,
]


# ER_MTN_TOTL_276

BASE_COLS_TOTL = BASE_COLS + [LULCCLASS]
