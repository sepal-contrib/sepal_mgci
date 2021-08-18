from importlib import reload
import ipyvuetify as v

import sepal_ui.mapping as sm
from sepal_ui.scripts import utils as su
from sepal_ui import sepalwidgets as sw

from component.widget.custom_widgets import *
from component.message import cm
from component.scripts import *

class MountainTile(v.Card, sw.SepalWidget):
    
    def __init__(self, model, *args, **kwargs):
        
        self._metadata={'mount_id': 'mountain_tile'}
        
        super().__init__(*args, **kwargs)
        
        # Class parameters
        self.model = model
        
        # Widgets
        self.alert = sw.Alert()
        
        # Card descriptors
        title = v.CardTitle(children=[cm.mountain_layer.title])
        description = v.CardText(children=[sw.Markdown(cm.mountain_layer.text)])
        
        self.w_select_dem = v.Select(
            label=cm.mountain_layer.w_dem.label,
            v_model='srtm_1',
            items=[
                {'text':cm.mountain_layer.w_dem.items[0], 'value':'custom'},
                {'text':cm.mountain_layer.w_dem.items[1], 'value':'srtm_1'},
                {'text':cm.mountain_layer.w_dem.items[2], 'value':'srtm_3'},
            ]
        )
        
        self.w_custom_dem = sw.AssetSelect(
            label="Select a custom DEM", types=["IMAGE"]
        ).hide()
        
        self.btn = sw.Btn('Create Kapos Layer')
        self.map_ = sm.SepalMap()
        
        # bind the widgets to the model
        self.model.bind(self.w_select_dem, 'dem_type')\
            .bind(self.w_custom_dem, 'custom_dem_id')

        self.children=[
            title,
            description,
            self.alert,
            self.w_select_dem,
            self.w_custom_dem,
            self.btn, 
            v.Card(children=[self.map_])
        ]
        
        # actions
        self.w_select_dem.observe(self.display_custom_dem, 'v_model')
        
        # Decorate functions
        self.get_kapos = su.loading_button(
            alert=self.alert, button=self.btn, debug=True
        )(self.get_kapos)
        
        self.btn.on_event('click', self.get_kapos)
    
    def display_custom_dem(self, change):
        """Display custom dem widget when w_select_dem == 'custom'"""
        
        v_model = change['new']
        self.w_custom_dem.show() if v_model == 'custom' else self.w_custom_dem.hide()
    
    def get_kapos(self, widget, event, data):
        """Create and display kapos layer on a map"""
        
        self.model.get_kapos()
        
        # Add kapos mountain layer to map
        
        vis_params = {
            'palette' : ['#D2222D', '#FFBF00', '#238823', '#007000'],
            'min':1,
            'max':7
        }
        
        self.map_.zoom_ee_object(self.model.aoi_model.feature_collection.geometry())
        self.map_.addLayer(self.model.kapos_image, vis_params, 'Kapos map')