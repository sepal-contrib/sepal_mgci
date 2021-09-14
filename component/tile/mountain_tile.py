from ipywidgets import Layout
import ipyvuetify as v

import sepal_ui.mapping as sm
from sepal_ui.scripts.utils import loading_button
from sepal_ui import sepalwidgets as sw

from component.message import cm
import component.parameter as param

__all__=['MountainTile']

class MountainTile(v.Card, sw.SepalWidget):
    
    def __init__(self, model, *args, **kwargs):
        
        self._metadata={'mount_id': 'mountain_tile'}
        self.class_ = 'pa-2'
        
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
            v_model='srtm_3',
            items=[
                {'text':cm.mountain_layer.w_dem.items[0], 'value':'custom'},
                {'text':cm.mountain_layer.w_dem.items[1], 'value':'srtm_1'},
                {'text':cm.mountain_layer.w_dem.items[2], 'value':'srtm_3'},
            ]
        )
        
        self.w_custom_dem = sw.AssetSelect(
            label="Select a custom DEM", types=["IMAGE"]
        ).hide()
        
        self.btn = sw.Btn(cm.mountain_layer.btn)
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
        self.add_kapos_map = loading_button(
            alert=self.alert, button=self.btn, debug=True
        )(self.add_kapos_map)
        
        self.btn.on_event('click', self.add_kapos_map)
    
    def display_custom_dem(self, change):
        """Display custom dem widget when w_select_dem == 'custom'"""
        
        v_model = change['new']
        self.w_custom_dem.show() if v_model == 'custom' else self.w_custom_dem.hide()
    
    def add_kapos_map(self, widget, event, data):
        """Create and display kapos layer on a map"""
        
        self.model.get_kapos()
        
        # Create legend
        self.map_.add_legend(
            legend_title="Legend", 
            legend_dict=param.KAPOS_LEGEND
        )
        # Do this trick to remove the scrolling bar in the legend output
        self.map_.legend_widget.layout = Layout(width='85px', overflow="none")
        
        # Add kapos mountain layer to map
        self.map_.zoom_ee_object(self.model.aoi_model.feature_collection.geometry())
        self.map_.addLayer(self.model.kapos_image, param.KAPOS_VIS, 'Kapos map')