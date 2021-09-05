from pathlib import Path

from traitlets import directional_link
from ipywidgets import Layout

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
            results_dir=param.CLASS_DIR, 
            save=False, 
            aoi_model=self.aoi_model,
            default_class = {
                'IPCC' : str(Path(__file__).parents[1]/'parameter/ipcc.csv'),
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
        self.display_map = loading_button(
            alert=sw.Alert(), button=self.btn, debug=True
        )(self.display_map)
        
        self.reclassify_tile.model.observe(self.update_model_vegetation, 'remaped')
        
        # Let's bind the selected band with the model, it will be useful in the dashboard
        
        
        directional_link((self.reclassify_tile.model, 'band'),(self.model, 'year'))
        directional_link((self.reclassify_tile.model, 'dst_class'),(self.model, 'lulc_classes'))
        
        self.btn.on_event('click', self.display_map)
    
    def update_model_vegetation(self, change):
        """Observe reclassify model, and update the mgci model. It will store
        the reclassified gee asset into the mgci model to perform operations.
        """
        if change['new']:

            self.model.vegetation_image = self.reclassify_tile\
                                            .reclassify_view.model.dst_gee_memory
            self.btn.disabled = False
        
    
    def display_map(self, *args):
        """Display reclassified raster on map. Get the reclassify visualization
        image."""
        
        # Create legend based on the lulc classes.
        self.map_.add_legend(
            legend_title="Legend", 
            legend_dict=dict(self.model.lulc_classes.values())
        )
        # Do this trick to remove the scrolling bar in the legend output
        self.map_.legend_widget.layout = Layout(width='120px', overflow="none")
        
        layer = self.reclassify_tile.reclassify_view.model.dst_gee_memory_vis
        
        #Remove previusly loaded layers
        [self.map_.remove_last_layer() for _ in range(len(self.map_.layers))]
        
        self.map_.zoom_ee_object(layer.geometry())
        self.map_.addLayer(layer)