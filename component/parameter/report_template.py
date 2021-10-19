# Stablish the template structure for the output tables.


### DEFINE DEFAULT VALUES ####
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
TIMEDETAIL = "Time_Detail"
SOURCE= "Source"
NATURE = "Nature"
REPORTING = "Reporting"


### DEFINE DEFAULT VALUES ####

INDICATOR_NUM = "15.4.2"
# Possible values for NATURE column
CUSTOM_="C" # When the user has his own lclu data
GLOBAL_="G" # When the user is using the default lulc data.

REPORTING_VALUE = "G" # Value return by the usage of this app.
NO_VALUE = "N" # None value for the VALUE column

### DEFINE REPORT COLUMNS ORDER ####

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
    TIMEDETAIL,
    SOURCE,
    "Footnote",
    NATURE,
    UNITSNAME,
    REPORTING,
    SERIESCOD,
    MOUNTAINCLASS,
]


# ER_MTN_TOTL_276

BASE_COLS_TOTL = BASE_COLS + [LULCCLASS]


# DEFAULT VALUES FOR TYPE OF REPORT

# ER_MTN_GRNCVI
SERIESDESC_GRNCVI = "Mountain Green Cover Index"
UNITSNAME_GRNCVI = "INDEX"
SERIESCOD_GRNCVI = "ER_MTN_GRNCVI"

#ER_MTN_GRNCOV
SERIESDESC_GRNCOV_1 = "Mountain green cover area ({unit})"
SERIESCOD_GRNCOV_1 = "ER_MTN_GRNCOV"
SERIESDESC_GRNCOV_2 = "Mountain area ({unit})"
SERIESCOD_GRNCOV_2 = "ER_MTN_TOTL"

#ER_MTN_TOTL
SERIESDESC_TTL = "Mountain area ({unit})"
SERIESCOD_TTL = "ER_MTN_TOTL"
