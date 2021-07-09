from traitlets import Unicode
from sepal_ui.model import Model


class MgciModel(Model):
    
    dem_layer = Unicode('').tag(sync=True)
    
    def __init__(self):
        
        self.kapos_image = None