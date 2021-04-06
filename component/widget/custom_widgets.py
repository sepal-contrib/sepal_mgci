import ipyvuetify as v
import ee
import sepal_ui.sepalwidgets as sw
from sepal_ui.scripts import utils as su

su.init_ee()

class AssetSelect(v.Combobox, sw.SepalWidget):
    """
    Custom widget input to select an asset inside the asset folder of the user
    
    Args:
        label (str): the label of the input
        folder (str): the folder of the user assets
        default_asset (str): the id of a default asset
        
    Attributes:
        folder (str): the folder of the user assets
    """
    
    def __init__(self, label = 'Select an asset', folder = None, default_asset = None, *args, **kwargs):
        
        # if folder is not set use the root one 
        self.folder = folder if folder else ee.data.getAssetRoots()[0]['id'] + '/'
        
        
        self.label = label
        self.v_model = default_asset
        
        self.clearable = True
        self.dense = True
        self.persistent_hint = True
        
        self.class_ = 'my-5'
        self.placeholder = 'users/someCustomUser/customAsset'
        self.hint = 'select an asset in the list or write a custom asset ' + \
                    'name. Be careful that you need to have access to this asset to use it'
        
        self.items = self._get_items()
        
        super().__init__(*args, **kwargs)

    def _get_items(self):
        
        # get the list of user asset
        assets = ee.data.listAssets({'parent': self.folder})['assets']
        
        tables = [e['id'] for e in assets if e['type'] == 'TABLE']
        images = [e['id'] for e in assets if e['type'] == 'IMAGE']
        
        items = [{'divider':True}, {'header':'Tables'}] + \
                tables + \
                [{'divider':True}, {'header':'Rasters'}] + \
                images
        
        return items
    
class Flex(v.Flex, sw.SepalWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)