from component.message import cm

# SET SOME PARAMETERS
UPPER_THRESHOLDS = {
    98:'green',
    95:'orange',
    90:'red'
}

IPCC_CLASSES = {
    # key: [name_key, translation, color]
    1: ['forest', cm.param.ipcc.forest, 'green'],
    2: ['grass', cm.param.ipcc.grass, 'purple'],
    3: ['crop', cm.param.ipcc.crop, 'orange'],
    4: ['wet', cm.param.ipcc.wet, 'blue'],
    5: ['settl', cm.param.ipcc.settl, 'gray'],
    6: ['other', cm.param.ipcc.other, 'white']
}

# Specify which are the IPCC green classes
# Forest, grassland, cropland, wetland

GREEN_CLASSES = [1,2,3,4]

CLASSES_COLOR = [v[2] for k, v in IPCC_CLASSES.items()]

# Classes that will be displayed in the dashboard
DISPLAY_CLASSES = [1,2,3,4,5,6]

KAPOS_PALETTE=['#ff0000', '#ff6f00', '#ffd500', '#bbff00', '#04ff00', '#034502']

KAPOS_LEGEND = {
    name:color for name, color 
    in zip([f'Kapos {i+1}' for i in range(6)], KAPOS_PALETTE)
}

#Kapos layer visualization for map
KAPOS_VIS = {
    'palette' : KAPOS_PALETTE,
    'min':1,
    'max':6
}






