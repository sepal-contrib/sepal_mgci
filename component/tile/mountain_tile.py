from importlib import reload
import ipyvuetify as v

import sepal_ui.mapping as sm
from sepal_ui.scripts import utils as su

from component.widget.custom_widgets import *
from component.message import cm
from component.scripts import *

class MountainTile(v.Card):
    
    def __init__(self, aoi, model, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Class parameters
        
        self.aoi = aoi.view.model
        self.model = model
        
        # Card descriptors
        title = v.CardTitle(children=[cm.mountain_layer.title])
        description = v.CardText(children=[sw.Markdown(cm.mountain_layer.text)])
        
        self.w_select_dem = v.Select(
            label=cm.mountain_layer.w_dem.label,
            v_model='srtm_1',
            items=[
#                 {'text':cm.mountain_layer.w_dem.items[0], 'value':'custom'},
                {'text':cm.mountain_layer.w_dem.items[1], 'value':'srtm_1'},
                {'text':cm.mountain_layer.w_dem.items[2], 'value':'srtm_3'},
#                 {'text':cm.mountain_layer.w_dem.items[3], 'value':'alos'},
            ]
        )
        
        self.btn = sw.Btn('Create Kapos Layer')
        self.map_ = sm.SepalMap()
        
        # bind the widgets to the model
        self.model.bind(self.w_select_dem, 'dem_layer')

        self.children=[
            title,
            description,
            self.w_select_dem,
            self.btn, 
            v.Card(children=[self.map_])
        ]
        
        # actions
#         self.w_select_dem.observe(self.display_custom_dem, 'v_model')
        
        # Decorate functions
        self.create_kapos = su.loading_button(
            alert=sw.Alert(), button=self.btn, debug=True
        )(self.create_kapos)
        
        self.btn.on_event('click', self.create_kapos)
    
#     def display_custom_dem(self, change):
#         """Display custom dem widget when w_select_dem == 'custom'"""
        
#         v_model = change['new']
#         self.w_custom_dem.show() if v_model == 'custom' else self.w_custom_dem.hide()
    
    def create_kapos(self, widget, event, data):
        """Create and display kapos layer on a map"""
        
        # Get the selected user aoi
        aoi = self.aoi.feature_collection
        dem = self.model.dem_layer
        
        self.model.kapos_image = get_kapos(aoi, dem)
        
        # Add kapos mountain layer to map
        
        vis_params = {
            'palette' : ['#D2222D', '#FFBF00', '#238823', '#007000'],
            'min':1,
            'max':7
        }
        
        self.map_.zoom_ee_object(aoi.geometry())
        self.map_.addLayer(self.model.kapos_image, vis_params, 'Kapos map')