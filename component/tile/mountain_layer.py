from importlib import reload
import ipyvuetify as v
from ..widget.custom_widgets import *
from ..message import cm

class MountainLayer(v.Card):
    
    def __init__(self, aoi, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Class parameters
        
        self.aoi = aoi
        
        # Card descriptors
        title = v.CardTitle(children=[cm.mountain_layer.title])
        description = v.CardText(children=[sw.Markdown(cm.mountain_layer.text)])
        
        self.w_select_dem = v.Select(
            label=cm.mountain_layer.w_dem.label,
            v_model='',
            items=[
                {'text':cm.mountain_layer.w_dem.items[0], 'value':'custom'},
                {'text':cm.mountain_layer.w_dem.items[1], 'value':'srtm_1'},
                {'text':cm.mountain_layer.w_dem.items[2], 'value':'srtm_3'},
                {'text':cm.mountain_layer.w_dem.items[3], 'value':'alos'},
            ]
        )
        
        self.w_custom_dem = AssetSelect(only='raster').hide()
        
        self.children=[
            title,
            description,
            self.w_select_dem,
            self.w_custom_dem
        ]
        
        self.w_select_dem.observe(self.display_custom_dem, 'v_model')
    
    def display_custom_dem(self, change):
        """Display custom dem widget when w_select_dem == 'custom'"""
        
        v_model = change['new']
        self.w_custom_dem.show() if v_model == 'custom' else self.w_custom_dem.hide()
        
        