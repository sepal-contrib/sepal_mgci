from pathlib import Path

import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.mapping as sm
from sepal_ui.scripts.utils import loading_button
from sepal_ui.reclassify import ReclassifyTile

from component.message import cm
import component.parameter as param


__all__ = ['VegetationTile']

class VegetationTile(v.Card, sw.SepalWidget):
    
    def __init__(self, model, aoi_model, *args, **kwargs):
        
        self._metadata={'mount_id': 'vegetation_tile'}

        self.class_ = 'pa-2'
        
        super().__init__(*args,  **kwargs)
                
        title = v.CardTitle(children=[cm.veg_layer.title])
        
        description = v.CardText(
            children=[sw.Markdown(cm.veg_layer.description)]
        )
        
        self.model = model
        self.aoi_model = aoi_model

        self.reclassify_tile = ReclassifyTile(
            results_dir=param.RESULTS_DIR, 
            save=False, 
            aoi_model=self.aoi_model,
            default_class = {
                'IPCC' : str(Path(__file__).parents[1]/'parameter/ipcc.csv'),
                'Forest/Non Forest' : str(Path(__file__).parents[1]/'parameter/binary.csv'),
            }
        )
        
        self.reclassify_tile.reclassify_view.w_asset.default_asset=[
            'users/geflanddegradation/toolbox_datasets/lcov_esacc_1992_2018'
        ]
        
        self.btn = sw.Btn('Display on map')
        self.btn.disabled = True
        
        self.map_ = sm.SepalMap()
        
        self.children=[
            title, 
            description,
            self.reclassify_tile,
            v.Card(class_='mt-2',
                children=[
                v.CardTitle(children=['Visualize results']),
                v.CardText(children=[self.btn, self.map_])
                
            ])
        ]
        
        #Decorate functions
        self.display_on_map = loading_button(
            alert=sw.Alert(), button=self.btn, debug=True
        )(self.display_on_map)
        
        self.reclassify_tile.model.observe(self.activate_display, 'remaped')
        self.btn.on_event('click', self.display_on_map)
        
    def activate_display(self, change):
        """Activate display button if an asset has been classified"""
        
        if change['new'] == True:
            self.btn.disabled = False
        else:
            self.btn.disabled = True        
    
    def display_on_map(self, widget, event, data):
        """Display reclassified raster on map"""
        
        layer = self.reclassify_tile.model.dst_gee_memory

        self.map_.zoom_ee_object(layer.geometry())
        self.map_.addLayer(layer)