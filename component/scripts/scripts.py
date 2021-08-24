import random
import ee
from sepal_ui.scripts import utils as su
from pandas import DataFrame
from component.parameter import *

ee.Initialize()
    
def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def get_mgci_color(mgci):
    """Return color based on a given MGCI scale"""
    
    thresholds = sorted(UPPER_THRESHOLDS, reverse=True)
    
    for threshold in thresholds:
        if mgci >= threshold:
            break
    
    return UPPER_THRESHOLDS[threshold]

def human_format(num, round_to=2):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return '{:.{}f}{}'.format(
        round(num, round_to), round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude]
    )


